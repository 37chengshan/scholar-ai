"""Batch storage manager for PDF pipeline.

Consolidates all storage operations into single transaction per paper:
- PostgreSQL: paper metadata, IMRaD, notes
- Milvus: text chunks, images, tables (batched)
- Neo4j: chunk nodes, section nodes

Per D-06: Batch storage reduces database round trips.
"""

import json
from typing import Any, Dict, List, Optional

import asyncpg

from app.workers.pipeline_context import PipelineContext
from app.core.milvus_service import get_milvus_service
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.docling_service import DoclingParser
from app.core.qwen3vl_service import get_qwen3vl_service
from app.utils.logger import logger


class StorageManager:
    """Batch storage manager for consolidated database writes."""
    
    EMBEDDING_DIM = 2048  # Qwen3VL dimension

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        milvus_service=None,
        neo4j_service=None,
        notes_generator=None
    ):
        """Initialize storage manager.
        
        Args:
            db_pool: PostgreSQL connection pool
            milvus_service: Milvus service (optional, uses singleton if None)
            neo4j_service: Neo4j service (optional, uses singleton if None)
            notes_generator: Notes generator (optional, uses singleton if None)
        """
        self.db_pool = db_pool
        self.milvus = milvus_service or get_milvus_service()
        self.neo4j = neo4j_service or Neo4jService()
        self.notes_generator = notes_generator or NotesGenerator()
        self.parser = DoclingParser()
        self.embedding_service = get_qwen3vl_service()

    async def store(self, ctx: PipelineContext) -> PipelineContext:
        """Store all extraction results in batch.
        
        Single transaction for:
        1. Paper metadata and IMRaD (PostgreSQL)
        2. Reading notes (PostgreSQL)
        3. All content vectors (Milvus batched)
        4. Graph nodes (Neo4j)
        
        Args:
            ctx: Pipeline context with extraction results
            
        Returns:
            Updated context
        """
        logger.info("Starting batch storage", task_id=ctx.task_id)
        
        async with self.db_pool.acquire() as conn:
            # 1. Update paper metadata and IMRaD
            await self._store_paper_metadata(conn, ctx)
            
            # 2. Generate and store reading notes
            await self._store_notes(conn, ctx)
        
        # 3. Store all content vectors in Milvus (batched)
        chunk_ids = await self._store_vectors(ctx)
        
        # 4. Store graph nodes in Neo4j
        await self._store_graph_nodes(ctx, chunk_ids)
        
        logger.info(
            "Batch storage complete",
            task_id=ctx.task_id,
            paper_id=ctx.paper_id
        )
        
        return ctx

    async def _store_paper_metadata(
        self,
        conn: asyncpg.Connection,
        ctx: PipelineContext
    ) -> None:
        """Update paper with metadata and IMRaD."""
        metadata = ctx.metadata or {}
        imrad = ctx.imrad or {}
        
        await conn.execute(
            """UPDATE papers
               SET content = $1,
                   page_count = $2,
                   status = 'processing',
                   imrad_json = $3,
                   title = COALESCE(NULLIF(title, ''), $4),
                   authors = COALESCE(NULLIF(authors, '{}'), $5),
                   abstract = COALESCE(NULLIF(abstract, ''), $6),
                   doi = COALESCE(NULLIF(doi, ''), $7),
                   keywords = COALESCE(NULLIF(keywords, '{}'), $8),
                   updated_at = NOW()
               WHERE id = $9""",
            ctx.parse_result.get("markdown", ""),
            ctx.parse_result.get("page_count", 0),
            json.dumps(imrad),
            metadata.get("title"),
            metadata.get("authors", []),
            metadata.get("abstract"),
            metadata.get("doi"),
            metadata.get("keywords", []),
            ctx.paper_id
        )
        
        logger.debug(
            "Paper metadata stored",
            task_id=ctx.task_id,
            paper_id=ctx.paper_id
        )

    async def _store_notes(
        self,
        conn: asyncpg.Connection,
        ctx: PipelineContext
    ) -> None:
        """Generate and store reading notes."""
        try:
            paper_metadata = {
                "title": ctx.metadata.get("title", "Unknown") if ctx.metadata else "Unknown",
                "authors": ctx.metadata.get("authors", []) if ctx.metadata else [],
                "year": ctx.metadata.get("year", "") if ctx.metadata else "",
                "venue": ctx.metadata.get("venue", "") if ctx.metadata else "",
            }
            
            notes = await self.notes_generator.generate_notes(
                paper_metadata=paper_metadata,
                imrad_structure=ctx.imrad or {}
            )
            
            if notes:
                await conn.execute(
                    """UPDATE papers
                       SET reading_notes = $1,
                           notes_version = notes_version + 1,
                           updated_at = NOW()
                       WHERE id = $2""",
                    notes,
                    ctx.paper_id
                )
                
                ctx.notes = notes
                
                logger.debug(
                    "Reading notes stored",
                    task_id=ctx.task_id,
                    notes_length=len(notes)
                )
                
        except Exception as e:
            logger.warning(
                "Failed to generate notes, continuing without",
                task_id=ctx.task_id,
                error=str(e)
            )

    async def _store_vectors(self, ctx: PipelineContext) -> List[int]:
        """Store all content vectors in Milvus (batched).
        
        Per D-06, D-27: Single batched insert for text, images, tables.
        """
        all_contents = []
        
        # 1. Generate text chunks from parsed content
        chunks = self.parser.chunk_by_semantic(
            ctx.parse_result["items"],
            paper_id=ctx.paper_id,
            imrad_structure=ctx.imrad
        )
        
        # Assign sections based on IMRaD
        for chunk in chunks:
            page = chunk.get("page_start")
            if page and ctx.imrad:
                for section_name, section_data in ctx.imrad.items():
                    if section_name.startswith("_"):
                        continue
                    if isinstance(section_data, dict):
                        start = section_data.get("page_start", 0)
                        end = section_data.get("page_end", 999)
                        if start and end and start <= page <= end:
                            chunk["section"] = section_name
                            break
            
            # Generate embedding for chunk
            chunk_text = chunk.get("text", "")
            try:
                embedding = self.embedding_service.encode_text(chunk_text)
            except Exception as e:
                logger.warning(
                    "Failed to generate chunk embedding",
                    error=str(e)
                )
                embedding = [0.0] * self.EMBEDDING_DIM
            
            all_contents.append({
                "paper_id": ctx.paper_id,
                "user_id": ctx.user_id,
                "content_type": "text",
                "page_num": chunk.get("page_start", 0),
                "section": chunk.get("section", ""),
                "text": chunk_text,
                "content_data": chunk_text[:8000],
                "embedding": embedding,
            })
        
        # 2. Add images
        if ctx.image_results:
            all_contents.extend(ctx.image_results)
        
        # 3. Add tables
        if ctx.table_results:
            all_contents.extend(ctx.table_results)
        
        # 4. Batch insert to Milvus
        if all_contents:
            chunk_ids = self.milvus.insert_contents_batched(all_contents)
            
            logger.info(
                "Vectors stored in Milvus",
                task_id=ctx.task_id,
                total=len(all_contents),
                chunks=len(chunks),
                images=len(ctx.image_results or []),
                tables=len(ctx.table_results or [])
            )
            
            ctx.chunk_results = all_contents[:len(chunks)]
            return chunk_ids
        
        return []

    async def _store_graph_nodes(
        self,
        ctx: PipelineContext,
        chunk_ids: List[int]
    ) -> None:
        """Store chunk and section nodes in Neo4j."""
        if not chunk_ids:
            return
        
        try:
            # Create chunk nodes
            chunks_with_ids = [
                {"id": cid, **chunk}
                for chunk, cid in zip(
                    ctx.parse_result.get("items", [])[:len(chunk_ids)],
                    chunk_ids
                )
            ]
            
            await self.neo4j.create_chunk_nodes(ctx.paper_id, chunks_with_ids)
            
            # Create section nodes
            section_data = {
                k: v for k, v in (ctx.imrad or {}).items()
                if not k.startswith("_") and isinstance(v, dict)
            }
            
            if section_data:
                await self.neo4j.create_section_nodes(ctx.paper_id, section_data)
            
            # Create paper node
            metadata = ctx.metadata or {}
            await self.neo4j.create_paper_node(
                paper_id=ctx.paper_id,
                title=metadata.get("title", "Untitled"),
                authors=metadata.get("authors", []),
                year=metadata.get("year")
            )
            
            logger.debug(
                "Graph nodes stored",
                task_id=ctx.task_id,
                chunks=len(chunks_with_ids)
            )
            
        except Exception as e:
            logger.warning(
                "Neo4j storage failed, continuing",
                task_id=ctx.task_id,
                error=str(e)
            )


# Singleton
_storage_manager: Optional[StorageManager] = None


def get_storage_manager(db_pool: asyncpg.Pool = None) -> StorageManager:
    """Get or create StorageManager singleton.
    
    Args:
        db_pool: PostgreSQL connection pool (required on first call)
        
    Returns:
        StorageManager instance
    """
    global _storage_manager
    if _storage_manager is None and db_pool:
        _storage_manager = StorageManager(db_pool)
    return _storage_manager