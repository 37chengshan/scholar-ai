"""PDF processing worker

Async worker for processing PDF tasks through the pipeline:
pending → processing_ocr → parsing → extracting_imrad → generating_notes → storing_vectors → indexing_multimodal → completed

Features:
- Downloads PDF from object storage
- Parses with Docling (OCR enabled)
- Updates task status through each stage
- Auto-retry on failure (3 attempts)
- Cleans up temp files after processing
- Stores chunks in PGVector and Neo4j
- Indexes images and tables in Milvus (multimodal)
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

from app.core.storage import ObjectStorage
from app.core.docling_service import DoclingParser
from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.imrad_extractor import (
    extract_imrad_structure,  # Keep for backward compatibility
    extract_imrad_enhanced,   # NEW: enhanced version per D-05
    extract_metadata
)
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.milvus_service import get_milvus_service
from app.core.image_extractor import ImageExtractor
from app.core.table_extractor import TableExtractor
from app.core.multimodal_indexer import MultimodalIndexer, get_multimodal_indexer
from app.core.semantic_scholar_service import get_semantic_scholar_service
from app.utils.logger import logger


def fuzzy_match_title(target: str, candidates: List[Dict], threshold: float = 0.8) -> Optional[Dict]:
    """Find best matching paper by title similarity.
    
    Per D-09: Similarity threshold 80%.
    
    Args:
        target: Target title to match
        candidates: List of candidate papers with 'title' field
        threshold: Minimum similarity ratio (0.0-1.0)
        
    Returns:
        Best matching paper or None
    """
    best_match = None
    best_ratio = 0.0
    
    for candidate in candidates:
        candidate_title = candidate.get("title", "")
        if not candidate_title:
            continue
        
        ratio = SequenceMatcher(None, target.lower(), candidate_title.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = candidate
    
    return best_match


class PDFProcessor:
    """PDF task processor with retry logic."""

    MAX_RETRIES = 3

    def __init__(self):
        self.storage = ObjectStorage()
        self.parser = DoclingParser()
        self.embedding_service = get_qwen3vl_service()
        self.neo4j_service = Neo4jService()
        self.notes_generator = NotesGenerator()
        self.milvus_service = get_milvus_service()
        self.image_extractor = ImageExtractor()
        self.table_extractor = TableExtractor()
        self.multimodal_indexer: Optional[MultimodalIndexer] = None
        self.db_pool: Optional[asyncpg.Pool] = None

    async def init_db(self):
        """Initialize database connection pool."""
        if not self.db_pool:
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://scholarai:scholarai123@localhost:5432/scholarai",
            )
            self.db_pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10,
            )

    async def enrich_metadata_if_needed(
        self,
        conn,
        paper_id: str,
        title: Optional[str],
        authors: List[str]
    ) -> bool:
        """Enrich paper metadata using Semantic Scholar.
        
        Per D-07: Triggered after PDF parsing.
        Per D-08: Only when title or authors missing.
        Per D-09: Fuzzy match with 80% threshold.
        
        Args:
            conn: Database connection
            paper_id: Paper UUID
            title: Extracted title (may be None)
            authors: Extracted authors list (may be empty)
            
        Returns:
            True if enrichment succeeded, False otherwise
        """
        # Per D-08: Skip if metadata complete
        if title and authors:
            logger.info("Metadata already complete, skipping enrichment", paper_id=paper_id)
            return False
        
        if not title:
            logger.info("No title to search with", paper_id=paper_id)
            return False
        
        try:
            s2_service = get_semantic_scholar_service()
            
            # Search S2 by title
            logger.info("Searching Semantic Scholar for metadata", title=title[:50])
            search_results = await s2_service.search_papers(
                query=title,
                fields="paperId,title,year,authors,abstract,citationCount,venue,publicationDate",
                limit=5
            )
            
            candidates = search_results.get("data", [])
            if not candidates:
                logger.info("No S2 search results found", title=title[:50])
                return False
            
            # Per D-09: Fuzzy match
            best_match = fuzzy_match_title(title, candidates, threshold=0.8)
            if not best_match:
                logger.info("No matching paper found above threshold", title=title[:50])
                return False
            
            # Update database with enriched metadata
            paper_id_s2 = best_match.get("paperId")
            enriched_title = best_match.get("title", title)
            enriched_year = best_match.get("year")
            enriched_abstract = best_match.get("abstract")
            citation_count = best_match.get("citationCount", 0)
            venue = best_match.get("venue")
            
            # Extract authors
            s2_authors = best_match.get("authors", [])
            author_names = [a.get("name") for a in s2_authors if a.get("name")]
            
            # Update paper record
            await conn.execute(
                """
                UPDATE papers 
                SET title = COALESCE($2, title),
                    year = COALESCE($3, year),
                    abstract = COALESCE($4, abstract),
                    s2_paper_id = $5,
                    citation_count = $6,
                    venue = $7,
                    updated_at = NOW()
                WHERE id = $1
                """,
                paper_id,
                enriched_title if enriched_title != title else None,
                enriched_year,
                enriched_abstract,
                paper_id_s2,
                citation_count,
                venue
            )
            
            logger.info(
                "Paper metadata enriched",
                paper_id=paper_id,
                s2_id=paper_id_s2,
                citations=citation_count
            )
            
            return True
            
        except Exception as e:
            # Per D-09: Don't block PDF processing on enrichment failure
            logger.error("Metadata enrichment failed", paper_id=paper_id, error=str(e))
            return False

    async def process_pdf_task(self, task_id: str) -> bool:
        """
        Process a single PDF task through all stages.

        Args:
            task_id: UUID of the processing task

        Returns:
            True if successful, False otherwise
        """
        await self.init_db()

        logger.info("Starting PDF processing", task_id=task_id)

        async with self.db_pool.acquire() as conn:
            task = await conn.fetchrow(
                """SELECT pt.*, p.user_id, p.id as paper_id, p.storage_key
                   FROM processing_tasks pt
                   JOIN papers p ON pt.paper_id = p.id
                   WHERE pt.id = $1""",
                task_id,
            )

        if not task:
            logger.error("Task not found", task_id=task_id)
            return False

        paper_id = task["paper_id"]
        storage_key = task["storage_key"]
        local_path = None

        try:
            # Stage 1: Download from object storage
            await self._update_status(task_id, "processing_ocr")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                await self.storage.download_file(storage_key, tmp.name)
                local_path = tmp.name
                file_size = os.path.getsize(tmp.name)
                logger.info(
                    "Downloaded PDF",
                    task_id=task_id,
                    size_bytes=file_size,
                )

            # Stage 2: OCR + Parsing
            await self._update_status(task_id, "parsing")
            parsed = await self.parser.parse_pdf(local_path)
            logger.info(
                "Parsed PDF",
                task_id=task_id,
                pages=parsed["page_count"],
                items=len(parsed["items"]),
            )
            
            # Extract metadata early for enrichment check
            metadata = extract_metadata(parsed["items"])

            # Stage 3: Store parsed content in papers table
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """UPDATE papers
                       SET content = $1, page_count = $2, status = 'processing'
                       WHERE id = $3""",
                    parsed["markdown"],
                    parsed["page_count"],
                    paper_id,
                )

            # Per D-07: Metadata enrichment after parsing
            # Enrich if title or authors are missing
            title = metadata.get("title")
            authors = metadata.get("authors", [])
            
            async with self.db_pool.acquire() as conn:
                await self.enrich_metadata_if_needed(conn, paper_id, title, authors)

            # Stage 4: Enhanced IMRaD extraction with LLM assistance per D-05
            await self._update_status(task_id, "extracting_imrad")
            
            # Use enhanced extraction for +85% non-standard paper recognition
            imrad = await extract_imrad_enhanced(
                items=parsed["items"],
                markdown=parsed["markdown"],
                paper_metadata=metadata
            )
            
            # Debug: Check if metadata is None
            if metadata is None:
                logger.error("Metadata is None", task_id=task_id)
                metadata = {
                    "title": None,
                    "authors": [],
                    "abstract": None,
                    "keywords": [],
                    "doi": None,
                }
            
            logger.info(
                "IMRaD extraction complete",
                task_id=task_id,
                confidence=imrad.get("_confidence_score", 0) if imrad else 0,
                estimated=imrad.get("_estimated", False) if imrad else False,
            )

            # Store IMRaD structure and update metadata in papers table
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """UPDATE papers
                       SET imrad_json = $1,
                           title = COALESCE(NULLIF(title, ''), $2),
                           authors = COALESCE(NULLIF(authors, '{}'), $3),
                           abstract = COALESCE(NULLIF(abstract, ''), $4),
                           doi = COALESCE(NULLIF(doi, ''), $5),
                           keywords = COALESCE(NULLIF(keywords, '{}'), $6)
                       WHERE id = $7""",
                    json.dumps(imrad),
                    metadata.get("title"),
                    metadata.get("authors", []),
                    metadata.get("abstract"),
                    metadata.get("doi"),
                    metadata.get("keywords", []),
                    paper_id,
                )

            # Stage 5: Generate Reading Notes
            await self._update_status(task_id, "generating_notes")

            # Prepare paper metadata for notes generation
            paper_metadata = {
                "title": metadata.get("title", "Unknown"),
                "authors": metadata.get("authors", []),
                "year": metadata.get("year", ""),
                "venue": metadata.get("venue", ""),
            }

            try:
                notes = await self.notes_generator.generate_notes(
                    paper_metadata=paper_metadata,
                    imrad_structure=imrad
                )
                logger.info(
                    "Generated reading notes",
                    task_id=task_id,
                    paper_id=paper_id,
                    notes_length=len(notes) if notes else 0,
                )
            except Exception as e:
                logger.error(
                    "Failed to generate notes, continuing without notes",
                    task_id=task_id,
                    error=str(e),
                )
                notes = None

            # Update paper with reading notes
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """UPDATE papers
                       SET reading_notes = $1,
                           notes_version = notes_version + 1
                       WHERE id = $2""",
                    notes,
                    paper_id,
                )

            # Stage 6: Chunking + Embeddings + Vector Storage
            await self._update_status(task_id, "storing_vectors")
            logger.info("Starting chunking and embedding", task_id=task_id)

            # Extract whole document markdown for contextual embeddings (Gap 1)
            whole_document = parsed.get("markdown", "")

            # Chunking strategy: Semantic splitting with LlamaIndex (per D-03)
            # Parameters: buffer_size=1, breakpoint_percentile_threshold=95
            # Overlap: 100 tokens for context continuity
            chunks = self.parser.chunk_by_semantic(
                parsed["items"],
                paper_id=paper_id,
                imrad_structure=imrad if imrad else None
            )

            # Assign section to each chunk based on page overlap with IMRaD
            for chunk in chunks:
                page = chunk.get("page_start")
                if page and imrad:
                    for section_name, section_data in imrad.items():
                        # Skip metadata fields
                        if section_name.startswith("_"):
                            continue
                        if isinstance(section_data, dict):
                            start = section_data.get("page_start", 0)
                            end = section_data.get("page_end", 999)
                            if start and end and start <= page <= end:
                                chunk["section"] = section_name
                                break

            logger.info(
                "Chunks created",
                task_id=task_id,
                chunk_count=len(chunks)
            )

            # Store chunks in Milvus with embeddings (Gap 1: contextual embeddings)
            chunk_ids = await self.embedding_service.store_chunks(
                paper_id=paper_id,
                user_id=task["user_id"],
                chunks=chunks,
                whole_document=whole_document  # Pass whole document for contextual embedding
            )

            logger.info(
                "Chunks stored in PostgreSQL",
                task_id=task_id,
                chunk_ids=len(chunk_ids)
            )

            # Store chunks in Neo4j for graph relationships
            chunks_with_ids = [
                {**chunk, "id": cid}
                for chunk, cid in zip(chunks, chunk_ids)
            ]
            await self.neo4j_service.create_chunk_nodes(paper_id, chunks_with_ids)

            # Create section nodes in Neo4j
            section_data_for_neo4j = {
                k: v for k, v in imrad.items()
                if not k.startswith("_") and isinstance(v, dict)
            }
            await self.neo4j_service.create_section_nodes(paper_id, section_data_for_neo4j)

            # Create paper node in Neo4j (if not exists)
            # Get paper metadata from database
            async with self.db_pool.acquire() as conn:
                paper_row = await conn.fetchrow(
                    "SELECT title, authors, year FROM papers WHERE id = $1",
                    paper_id
                )
                if paper_row:
                    authors = paper_row["authors"] if paper_row["authors"] else []
                    if isinstance(authors, str):
                        authors = [a.strip() for a in authors.split(",")]
                    await self.neo4j_service.create_paper_node(
                        paper_id=paper_id,
                        title=paper_row["title"] or "Untitled",
                        authors=authors,
                        year=paper_row["year"]
                    )

            logger.info(
                "Graph storage complete",
                task_id=task_id,
                chunks_in_neo4j=len(chunks_with_ids)
            )

            # Stage 7: Multimodal Indexing (Images and Tables)
            await self._update_status(task_id, "indexing_multimodal")
            logger.info("Starting multimodal indexing", task_id=task_id)

            try:
                # Initialize multimodal indexer if needed
                if not self.multimodal_indexer:
                    self.multimodal_indexer = get_multimodal_indexer()

                # Index all multimodal content
                index_results = await self.multimodal_indexer.index_paper(
                    paper_id=paper_id,
                    user_id=task["user_id"],
                    pdf_path=local_path,
                    parsed_items=parsed["items"],
                    paper_markdown=parsed.get("markdown")  # Pass markdown for D-04 context
                )

                # Store partial failures if any
                if index_results.get("partial_failures"):
                    await self._store_partial_failures(
                        task_id,
                        index_results["partial_failures"]
                    )

                logger.info(
                    "Multimodal indexing complete",
                    task_id=task_id,
                    images_indexed=index_results["images_indexed"],
                    tables_indexed=index_results["tables_indexed"],
                    failures=len(index_results.get("partial_failures", []))
                )

            except Exception as e:
                # Log error but don't fail the PDF processing (tiered failure per D-29)
                logger.error(
                    "Multimodal indexing failed",
                    task_id=task_id,
                    error=str(e)
                )
                await self._store_partial_failures(task_id, [{
                    "type": "indexing",
                    "error": str(e)
                }])

            # Mark complete
            await self._update_status(task_id, "completed")
            logger.info(
                "PDF processing complete",
                task_id=task_id,
                paper_id=paper_id,
                chunks_stored=len(chunks),
                notes_generated=notes is not None,
            )

            return True

        except Exception as e:
            logger.error(
                "PDF processing failed",
                task_id=task_id,
                error=str(e),
            )
            await self._update_status(task_id, "failed", error=str(e))
            return False

        finally:
            # Cleanup temp file
            if local_path:
                try:
                    Path(local_path).unlink(missing_ok=True)
                    logger.debug("Cleaned up temp file", path=local_path)
                except Exception as e:
                    logger.warning(
                        "Failed to cleanup temp file",
                        path=local_path,
                        error=str(e),
                    )

    async def _update_status(
        self, task_id: str, status: str, error: Optional[str] = None
    ):
        """
        Update task status in database.

        Args:
            task_id: Task UUID
            status: New status
            error: Optional error message
        """
        async with self.db_pool.acquire() as conn:
            completed_at = None
            if status == "completed":
                completed_at = datetime.now()

            await conn.execute(
                """UPDATE processing_tasks
                   SET status = $1,
                       updated_at = NOW(),
                       error_message = $2,
                       completed_at = COALESCE($3::timestamp, completed_at)
                   WHERE id = $4""",
                status,
                error,
                completed_at,
                task_id,
            )

        logger.info("Task status updated", task_id=task_id, status=status)

    async def _store_partial_failures(
        self,
        task_id: str,
        failures: List[Dict[str, Any]]
    ) -> None:
        """Store partial failures in processing_tasks table.

        Args:
            task_id: Task UUID
            failures: List of failure records
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE processing_tasks
                   SET partial_failures = $1::jsonb,
                       updated_at = NOW()
                   WHERE id = $2""",
                json.dumps({"failures": failures}),
                task_id
            )
        logger.info(
            "Stored partial failures",
            task_id=task_id,
            failure_count=len(failures)
        )

    async def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task if attempts remaining.

        Args:
            task_id: Task UUID to retry

        Returns:
            True if retry initiated, False if max retries exceeded
        """
        await self.init_db()

        async with self.db_pool.acquire() as conn:
            task = await conn.fetchrow(
                """SELECT attempts, status
                   FROM processing_tasks
                   WHERE id = $1""",
                task_id,
            )

            if not task:
                logger.error("Task not found for retry", task_id=task_id)
                return False

            if task["attempts"] >= self.MAX_RETRIES:
                logger.error(
                    "Max retries exceeded",
                    task_id=task_id,
                    attempts=task["attempts"],
                )
                return False

            # Increment attempts and reset to pending
            await conn.execute(
                """UPDATE processing_tasks
                   SET status = 'pending',
                       attempts = attempts + 1,
                       error_message = NULL,
                       updated_at = NOW()
                   WHERE id = $1""",
                task_id,
            )

        logger.info(
            "Task queued for retry",
            task_id=task_id,
            attempt=task["attempts"] + 1,
        )
        return True


# Worker loop for standalone execution
async def worker_loop():
    """Main worker loop - polls for pending tasks."""
    processor = PDFProcessor()
    await processor.init_db()

    logger.info("PDF worker started")

    POLL_INTERVAL = 5  # seconds

    while True:
        try:
            async with processor.db_pool.acquire() as conn:
                # Fetch next pending task with row locking
                task = await conn.fetchrow(
                    """UPDATE processing_tasks
                       SET status = 'processing_ocr',
                           updated_at = NOW()
                       WHERE id = (
                           SELECT id FROM processing_tasks
                           WHERE status = 'pending'
                           ORDER BY created_at ASC
                           FOR UPDATE SKIP LOCKED
                           LIMIT 1
                       )
                       RETURNING *"""
                )

            if task:
                logger.info("Processing task", task_id=task["id"])
                try:
                    success = await processor.process_pdf_task(task["id"])
                    if not success:
                        # Try retry if failed
                        await processor.retry_task(task["id"])
                except Exception as e:
                    logger.error(
                        "Task processing error",
                        task_id=task["id"],
                        error=str(e),
                    )
                    await processor.retry_task(task["id"])
            else:
                # No pending tasks, sleep before polling again
                await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error("Worker loop error", error=str(e))
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(worker_loop())
