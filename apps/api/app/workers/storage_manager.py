"""Batch storage manager for PDF pipeline.

Consolidates all storage operations into single transaction per paper:
- PostgreSQL: paper metadata, IMRaD, notes
- Milvus: text chunks, images, tables (batched)
- Neo4j: chunk nodes, section nodes

Per D-06: Batch storage reduces database round trips.
"""

import json
import re
from typing import Any, Dict, List, Optional

import asyncpg

from app.workers.pipeline_context import PipelineContext
from app.core.milvus_service import get_milvus_service, calculate_chunk_quality
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.docling_service import DoclingParser
from app.core.qwen3vl_service import get_qwen3vl_service
from app.utils.logger import logger


class StorageManager:
    """Batch storage manager for consolidated database writes."""

    EMBEDDING_DIM = 2048  # Qwen3VL dimension
    MIN_CHUNK_QUALITY = 0.25

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        milvus_service=None,
        neo4j_service=None,
        notes_generator=None,
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

        # Get or create Qwen3VL service and ensure model is loaded
        self.qwen3vl_service = get_qwen3vl_service()
        if not self.qwen3vl_service.is_loaded():
            logger.info("Loading Qwen3VL model in storage manager...")
            self.qwen3vl_service.load_model()
            logger.info("Qwen3VL model loaded in storage manager")

    @staticmethod
    def _build_evidence_metadata(
        chunk: Dict[str, Any],
        chunk_text: str,
        parse_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build evidence-level metadata for downstream retrieval/verifier stages."""
        section = chunk.get("section") or ""
        page_num = chunk.get("page_start") or 0
        snippet = chunk_text.replace("\n", " ").strip()
        anchor_text = snippet[:200]

        figure_match = re.search(r"\b(?:figure|fig\.)\s*(\d+)\b", snippet, re.IGNORECASE)
        table_match = re.search(r"\btable\s*(\d+)\b", snippet, re.IGNORECASE)
        figure_id = f"figure-{figure_match.group(1)}" if figure_match else None
        table_id = f"table-{table_match.group(1)}" if table_match else None

        caption_match = re.search(
            r"\b(?:figure|fig\.|table)\s*\d+\s*[:.-]\s*([^\n.]{1,120})",
            chunk_text,
            re.IGNORECASE,
        )
        caption = caption_match.group(1).strip() if caption_match else None

        source_span = {
            "start_char": 0,
            "end_char": min(len(chunk_text), 200),
        }

        nearby_explanation = ""
        lower_snippet = snippet.lower()
        if "figure" in lower_snippet or "fig." in lower_snippet:
            nearby_explanation = "contains_figure_reference"
        elif "table" in lower_snippet:
            nearby_explanation = "contains_table_reference"

        return {
            "evidence_version": "v1",
            "content_subtype": "paragraph",
            "section_path": section,
            "anchor_text": anchor_text,
            "source_span": source_span,
            "figure_id": figure_id,
            "table_id": table_id,
            "caption": caption,
            "nearby_explanation": nearby_explanation,
            "parse_mode": parse_metadata.get("parse_mode"),
            "ocr_used": parse_metadata.get("ocr_used"),
            "parse_warnings": parse_metadata.get("parse_warnings", []),
            "chunk_strategy": parse_metadata.get("chunk_strategy", {}),
            "page_num": page_num,
        }

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
            "Batch storage complete", task_id=ctx.task_id, paper_id=ctx.paper_id
        )

        return ctx

    async def _store_paper_metadata(
        self, conn: asyncpg.Connection, ctx: PipelineContext
    ) -> None:
        """Update paper with metadata and IMRaD.

        Per D-04: Always update title from extracted metadata when available.
        Filename-based title should be replaced with extracted title from PDF.
        """
        metadata = ctx.metadata or {}
        imrad = ctx.imrad or {}

        # Extract title from metadata, convert empty strings to None
        extracted_title = metadata.get("title")
        if extracted_title and isinstance(extracted_title, str):
            extracted_title = extracted_title.strip() or None

        # Per D-04: Use extracted title if available (overwrites filename-based title)
        # Only fallback to existing title if extraction truly failed
        title_update_clause = "title = $4" if extracted_title else "title = title"

        await conn.execute(
            f"""UPDATE papers
               SET content = $1,
                   "pageCount" = $2,
                   status = 'processing',
                   "imradJson" = $3,
                   {title_update_clause},
                   authors = COALESCE(NULLIF($5::text[], '{{}}'), authors),
                   abstract = COALESCE(NULLIF($6, ''), abstract),
                   doi = COALESCE(NULLIF($7, ''), doi),
                   keywords = COALESCE(NULLIF($8::text[], '{{}}'), keywords),
                   "updatedAt" = NOW()
               WHERE id = $9""",
            ctx.parse_result.get("markdown", ""),
            ctx.parse_result.get("page_count", 0),
            json.dumps(imrad),
            extracted_title,  # $4 - only used if title_update_clause is "title = $4"
            metadata.get("authors", []),
            metadata.get("abstract"),
            metadata.get("doi"),
            metadata.get("keywords", []),
            ctx.paper_id,
        )

        logger.debug(
            "Paper metadata stored", task_id=ctx.task_id, paper_id=ctx.paper_id
        )

    async def _store_notes(
        self, conn: asyncpg.Connection, ctx: PipelineContext
    ) -> None:
        """Generate and store reading notes."""
        try:
            paper_metadata = {
                "title": ctx.metadata.get("title", "Unknown")
                if ctx.metadata
                else "Unknown",
                "authors": ctx.metadata.get("authors", []) if ctx.metadata else [],
                "year": ctx.metadata.get("year", "") if ctx.metadata else "",
                "venue": ctx.metadata.get("venue", "") if ctx.metadata else "",
            }

            notes = await self.notes_generator.generate_notes(
                paper_metadata=paper_metadata, imrad_structure=ctx.imrad or {}
            )

            if notes:
                await conn.execute(
                    """UPDATE papers
                       SET reading_notes = $1,
                           notes_version = notes_version + 1,
                           "updatedAt" = NOW()
                       WHERE id = $2""",
                    notes,
                    ctx.paper_id,
                )

                ctx.notes = notes

                logger.debug(
                    "Reading notes stored", task_id=ctx.task_id, notes_length=len(notes)
                )

        except Exception as e:
            logger.warning(
                "Failed to generate notes, continuing without",
                task_id=ctx.task_id,
                error=str(e),
            )

    async def _store_vectors(self, ctx: PipelineContext) -> List[int]:
        """Store all content vectors in Milvus (batched).

        Per D-06, D-27: Single batched insert for text, images, tables.
        """
        all_contents = []
        text_contents = []
        parse_metadata = (ctx.parse_result or {}).get("metadata", {})
        parse_items = (ctx.parse_result or {}).get("items")

        if not isinstance(parse_items, list):
            logger.warning(
                "Missing parse_result.items, skipping vector storage",
                task_id=ctx.task_id,
            )
            if ctx.parse_result is None:
                ctx.parse_result = {}
            if not isinstance(ctx.parse_result.get("metadata"), dict):
                ctx.parse_result["metadata"] = {}
            ctx.parse_result["metadata"]["quality_gate"] = {
                "threshold": self.MIN_CHUNK_QUALITY,
                "input_chunks": 0,
                "indexed_chunks": 0,
                "skipped_chunks": 0,
                "image_records": len(ctx.image_results or []),
                "table_records": len(ctx.table_results or []),
                "skip_reason": "missing_parse_items",
            }
            return []

        # 1. Generate text chunks from parsed content
        chunks = self.parser.chunk_by_semantic(
            parse_items,
            paper_id=ctx.paper_id,
            imrad_structure=ctx.imrad,
        )

        # Assign sections based on IMRaD
        chunk_texts = []
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
                            chunk["section"] = (
                                section_name or ""
                            )  # Fix: Ensure non-None
                            break

            # Fix: Ensure section is never None after assignment attempts
            if chunk.get("section") is None:
                chunk["section"] = ""

            chunk_text = chunk.get("text", "")
            if not chunk_text or not chunk_text.strip():
                chunk_text = "NULL"
            chunk_texts.append(chunk_text)

        # Batch generate embeddings (much faster than one-by-one)
        logger.info(
            "Generating embeddings in batch",
            task_id=ctx.task_id,
            chunk_count=len(chunk_texts),
        )

        # CRITICAL: Ensure model is loaded on GPU before encoding
        if not self.qwen3vl_service.is_loaded():
            logger.warning("Model not loaded, loading now...")
            self.qwen3vl_service.load_model()

        # Verify GPU usage
        logger.info(
            f"Embedding model status - Loaded: {self.qwen3vl_service.is_loaded()}, Device: {self.qwen3vl_service.get_device()}"
        )

        # Generate embeddings in smaller batches to avoid GPU memory overflow
        # MPS on Mac has limited GPU memory allocation
        BATCH_SIZE = 8
        embeddings = []

        try:
            for i in range(0, len(chunk_texts), BATCH_SIZE):
                batch = chunk_texts[i : i + BATCH_SIZE]
                batch_embeddings = self.qwen3vl_service.encode_text(batch)
                embeddings.extend(batch_embeddings)

                # Clear GPU cache after each batch
                import torch

                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

            logger.info(
                "Embeddings generated", task_id=ctx.task_id, count=len(embeddings)
            )
        except Exception as e:
            logger.error(
                "Failed to generate batch embeddings", task_id=ctx.task_id, error=str(e)
            )
            embeddings = [[0.0] * self.EMBEDDING_DIM] * len(chunk_texts)

        if len(embeddings) != len(chunk_texts):
            logger.warning(
                "Embedding count mismatch, normalizing length",
                task_id=ctx.task_id,
                chunk_count=len(chunk_texts),
                embedding_count=len(embeddings),
            )
            if len(embeddings) < len(chunk_texts):
                padding = [[0.0] * self.EMBEDDING_DIM] * (len(chunk_texts) - len(embeddings))
                embeddings = embeddings + padding
            else:
                embeddings = embeddings[: len(chunk_texts)]

        # Add chunks with embeddings
        skipped_low_quality = 0
        for i, chunk in enumerate(chunks):
            chunk_text = chunk_texts[i]
            embedding = embeddings[i]

            # Fix: Handle None values in section field
            # When section is None, use empty string instead
            section = chunk.get("section") or ""

            quality_score = calculate_chunk_quality(
                {
                    "text": chunk_text,
                    "section": section,
                    "has_equations": chunk.get("has_equations", False),
                    "has_figures": chunk.get("has_figures", False),
                }
            )

            # PR7 quality gate: keep low-quality chunks out of main index.
            if quality_score < self.MIN_CHUNK_QUALITY:
                skipped_low_quality += 1
                continue

            raw_data = self._build_evidence_metadata(chunk, chunk_text, parse_metadata)

            text_record = {
                "paper_id": ctx.paper_id,
                "user_id": ctx.user_id,
                "content_type": "text",
                "page_num": chunk.get("page_start", 0),
                "section": section,
                "text": chunk_text,
                "content_data": chunk_text[:8000],
                "raw_data": raw_data,
                "embedding": embedding,
            }
            text_contents.append(text_record)
            all_contents.append(text_record)

        quality_gate = {
            "threshold": self.MIN_CHUNK_QUALITY,
            "input_chunks": len(chunks),
            "indexed_chunks": len(text_contents),
            "skipped_chunks": skipped_low_quality,
            "image_records": len(ctx.image_results or []),
            "table_records": len(ctx.table_results or []),
        }

        if ctx.parse_result is not None:
            if "metadata" not in ctx.parse_result:
                ctx.parse_result["metadata"] = {}
            ctx.parse_result["metadata"]["quality_gate"] = quality_gate

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
                indexed_chunks=len(text_contents),
                skipped_low_quality=skipped_low_quality,
                images=len(ctx.image_results or []),
                tables=len(ctx.table_results or []),
            )

            ctx.chunk_results = text_contents
            # Keep text chunk ids for graph linking, but preserve ids for image/table-only inserts.
            if text_contents:
                return chunk_ids[: len(text_contents)]
            return chunk_ids

        return []

    async def _store_graph_nodes(
        self, ctx: PipelineContext, chunk_ids: List[int]
    ) -> None:
        """Store chunk and section nodes in Neo4j."""
        if not chunk_ids or not (ctx.chunk_results or []):
            return

        try:
            # Create chunk nodes
            chunks_with_ids = [
                {"id": cid, **chunk}
                for chunk, cid in zip((ctx.chunk_results or [])[: len(chunk_ids)], chunk_ids)
            ]

            await self.neo4j.create_chunk_nodes(ctx.paper_id, chunks_with_ids)

            # Create section nodes
            section_data = {
                k: v
                for k, v in (ctx.imrad or {}).items()
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
                year=metadata.get("year"),
            )

            logger.debug(
                "Graph nodes stored", task_id=ctx.task_id, chunks=len(chunks_with_ids)
            )

        except Exception as e:
            logger.warning(
                "Neo4j storage failed, continuing", task_id=ctx.task_id, error=str(e)
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
