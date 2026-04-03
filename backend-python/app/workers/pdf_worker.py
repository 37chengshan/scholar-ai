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
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

from app.core.storage import ObjectStorage
from app.core.docling_service import DoclingParser
from app.core.embedding_service import EmbeddingService
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
from app.utils.logger import logger


class PDFProcessor:
    """PDF task processor with retry logic."""

    MAX_RETRIES = 3

    def __init__(self):
        self.storage = ObjectStorage()
        self.parser = DoclingParser()
        self.embedding_service = EmbeddingService()
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

            # Stage 4: Enhanced IMRaD extraction with LLM assistance per D-05
            await self._update_status(task_id, "extracting_imrad")
            metadata = extract_metadata(parsed["items"])
            
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

            # Store chunks in PostgreSQL with embeddings (Gap 1: contextual embeddings)
            async with self.db_pool.acquire() as conn:
                chunk_ids = await self.embedding_service.store_chunks(
                    conn, paper_id, chunks,
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
