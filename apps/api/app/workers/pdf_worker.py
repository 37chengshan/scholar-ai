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

# Load environment variables BEFORE any other imports
# Per CONTEXT.md specifics: Fix dotenv loading order
from dotenv import load_dotenv

load_dotenv()  # Must be called before any os.getenv() or module imports that use env vars

import asyncio
import json
import os
import tempfile
import warnings
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

from app.config import settings
from app.core.storage import ObjectStorage
from app.core.docling_service import DoclingParser
from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.imrad_extractor import (
    extract_imrad_structure,  # Keep for backward compatibility
    extract_imrad_enhanced,  # NEW: enhanced version per D-05
    extract_metadata,
)
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.milvus_service import get_milvus_service
from app.core.image_extractor import ImageExtractor
from app.core.table_extractor import TableExtractor
from app.core.multimodal_indexer import MultimodalIndexer, get_multimodal_indexer
from app.core.semantic_scholar_service import get_semantic_scholar_service
from app.workers.pdf_coordinator import PDFCoordinator, get_pdf_coordinator
from app.utils.logger import logger


def fuzzy_match_title(
    target: str, candidates: List[Dict], threshold: float = 0.8
) -> Optional[Dict]:
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


async def generate_reading_notes(
    paper_title: str, imrad_sections: Dict[str, Any], metadata: Dict[str, Any]
) -> str:
    """Generate five-paragraph reading notes limited to 500 characters.

    Per D-04: Five-paragraph format with character limit.

    Structure:
    1. Background (背景): Research context and motivation
    2. Methods (方法): Approach and methodology
    3. Results (结果): Key findings and contributions
    4. Discussion (讨论): Implications and limitations
    5. Key Contributions (关键贡献): Main takeaways

    Each paragraph: 2-3 sentences, ~100 characters.
    Total: ~500 characters.

    Args:
        paper_title: Paper title
        imrad_sections: Dict with introduction, methods, results, conclusion
        metadata: Paper metadata (year, venue, etc.)

    Returns:
        Five-paragraph reading notes (max 500 chars)

    Raises:
        Exception: If LLM call fails
    """
    from zhipuai import ZhipuAI
    from app.config import settings

    # Extract content from IMRaD sections (truncate to avoid token limits)
    intro_text = imrad_sections.get("introduction", {}).get("content", "")[:500]
    methods_text = imrad_sections.get("methods", {}).get("content", "")[:500]
    results_text = imrad_sections.get("results", {}).get("content", "")[:500]
    conclusion_text = imrad_sections.get("conclusion", {}).get("content", "")[:500]

    prompt = f"""为论文《{paper_title}》生成五段式阅读笔记，每段2-3句话，总计不超过500字。

格式要求：
【背景】研究背景和动机
【方法】研究方法和途径
【结果】主要发现和成果
【讨论】意义和局限性
【关键贡献】核心贡献

论文信息：
引言：{intro_text}
方法：{methods_text}
结果：{results_text}
结论：{conclusion_text}

请严格按照五段式格式输出，每段简洁明了。"""

    try:
        client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)
        response = client.chat.completions.create(
            model="glm-4.5-air",  # Per D-04
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,  # Limit output for ~500 char notes
        )

        notes = response.choices[0].message.content.strip()

        # Validate character limit per D-04
        if len(notes) > 500:
            notes = notes[:497] + "..."
            logger.info(
                "Reading notes truncated to 500 characters",
                paper_title=paper_title[:50],
                original_length=len(response.choices[0].message.content),
            )

        logger.info(
            "Generated five-paragraph reading notes",
            paper_title=paper_title[:50],
            length=len(notes),
        )

        return notes

    except Exception as e:
        logger.error(
            "Failed to generate reading notes",
            paper_title=paper_title[:50],
            error=str(e),
        )
        raise


class PDFProcessor:
    """PDF task processor with retry logic.

    This class now acts as a backward-compatible adapter for the
    parallel PDFCoordinator pipeline. All actual processing is
    delegated to PDFCoordinator.

    Per D-01: Refactored from serial to parallel architecture.
    Per D-13: Main/enhancement chain split for fast indexing + async quality.
    """

    MAX_RETRIES = 3

    def __init__(self):
        # Initialize coordinator for parallel processing
        self._coordinator: Optional[PDFCoordinator] = None
        self.db_pool: Optional[asyncpg.Pool] = None

    @property
    def coordinator(self) -> PDFCoordinator:
        """Lazy-load coordinator singleton."""
        if self._coordinator is None:
            self._coordinator = get_pdf_coordinator()
        return self._coordinator

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

    async def process_pdf_main_chain(
        self,
        task_id: str,
        temp_path: str,
        user_id: str,
    ) -> str:
        """Execute main chain: must complete for paper to be searchable.

        .. deprecated::
            Use ``process_pdf_task(task_id)`` which delegates to
            ``PDFCoordinator.process(task_id)``.  This method is retained for
            backward compatibility only and is not called by the official pipeline.
        """
        warnings.warn(
            "process_pdf_main_chain is deprecated; use process_pdf_task() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        await self.init_db()

        async with self.db_pool.acquire() as conn:
            # Get task info
            task = await conn.fetchrow(
                """SELECT pt.*, p.id as paper_id, p.storage_key
                   FROM processing_tasks pt
                   JOIN papers p ON pt.paper_id = p.id
                   WHERE pt.id = $1""",
                task_id,
            )

        if not task:
            raise ValueError(f"Task not found: {task_id}")

        paper_id = task["paper_id"]

        try:
            # Stage 1: Validate PDF (magic bytes, size)
            await self._validate_pdf(temp_path)

            # Stage 2: Parse with Docling
            parse_result = await self._parse_pdf(temp_path)

            # Stage 3: Chunk content
            chunks = await self._chunk_content(parse_result)

            # Stage 4: Embed text chunks
            embeddings = await self._embed_text_chunks(chunks)

            # Stage 5: Basic storage (PostgreSQL + Milvus)
            await self._store_chunks(chunks, embeddings, user_id, paper_id)

            logger.info(
                "Main chain completed",
                task_id=task_id,
                paper_id=paper_id,
                chunk_count=len(chunks),
            )

            # Update status to completed
            await self._update_status(task_id, "completed")

            # Per D-13: Trigger enhancement chain asynchronously
            asyncio.create_task(
                self.process_pdf_enhancement_chain(task_id, paper_id)
            )

            return paper_id

        except Exception as e:
            await self._update_status(task_id, "failed", error=str(e))
            logger.error("Main chain failed", task_id=task_id, error=str(e))
            raise

    async def process_pdf_enhancement_chain(
        self,
        task_id: str,
        paper_id: str,
    ) -> None:
        """Execute enhancement chain: async quality improvements.

        .. deprecated::
            Use ``process_pdf_task(task_id)`` which delegates to
            ``PDFCoordinator.process(task_id)``.  This method is retained for
            backward compatibility only and is not called by the official pipeline.
        """
        warnings.warn(
            "process_pdf_enhancement_chain is deprecated; use process_pdf_task() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            await self.init_db()

            async with self.db_pool.acquire() as conn:
                # Enhancement 1: Metadata enrichment
                await self._enrich_metadata(conn, paper_id)

                # Enhancement 2: Graph relations
                await self._update_graph_relations(paper_id)

                # Enhancement 3: Quality scoring
                await self._calculate_advanced_quality(paper_id)

            logger.info(
                "Enhancement chain completed",
                task_id=task_id,
                paper_id=paper_id,
            )

        except Exception as e:
            # Per D-13: Enhancement failure degrades gracefully
            logger.warning(
                "Enhancement chain failed (non-blocking)",
                task_id=task_id,
                paper_id=paper_id,
                error=str(e),
            )
            # Don't mark task as failed - main chain completed

    async def _validate_pdf(self, temp_path: str) -> None:
        """Validate PDF file (magic bytes, size)."""
        # Check magic bytes
        with open(temp_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF file (magic bytes check failed)")

        # Check file size
        file_size = os.path.getsize(temp_path)
        max_size = settings.PARSER_MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size / (1024*1024):.1f}MB exceeds limit")

        logger.debug("PDF validated", temp_path=temp_path, size_mb=file_size / (1024*1024))

    async def _parse_pdf(self, temp_path: str) -> Dict[str, Any]:
        """Parse PDF with Docling.

        .. deprecated:: Use ``PDFCoordinator.process()`` instead.
        """
        warnings.warn("_parse_pdf is deprecated; pipeline stages are handled by PDFCoordinator.", DeprecationWarning, stacklevel=2)
        parser = DoclingParser()
        result = await asyncio.wait_for(
            parser.parse_pdf(temp_path),
            timeout=settings.PARSER_TIMEOUT_SECONDS,
        )
        logger.debug("PDF parsed", page_count=result.get("page_count", 0))
        return result

    async def _chunk_content(self, parse_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk parsed content.

        .. deprecated:: Use ``PDFCoordinator.process()`` instead.
        """
        warnings.warn("_chunk_content is deprecated; pipeline stages are handled by PDFCoordinator.", DeprecationWarning, stacklevel=2)
        parser = DoclingParser()
        chunks = parser.chunk_by_semantic(
            parse_result["items"],
            paper_id="",  # Will be set later
            imrad_structure=None,
        )
        logger.debug("Content chunked", chunk_count=len(chunks))
        return chunks

    async def _embed_text_chunks(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Embed text chunks with Qwen3VL.

        .. deprecated:: Use ``PDFCoordinator.process()`` instead.
        """
        warnings.warn("_embed_text_chunks is deprecated; pipeline stages are handled by PDFCoordinator.", DeprecationWarning, stacklevel=2)
        qwen3vl = get_qwen3vl_service()
        texts = [chunk.get("text", "") for chunk in chunks]
        embeddings = qwen3vl.encode_text(texts)
        logger.debug("Chunks embedded", count=len(embeddings))
        return embeddings

    async def _store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        user_id: str,
        paper_id: str,
    ) -> None:
        """Store chunks in Milvus.

        .. deprecated:: Use ``PDFCoordinator.process()`` instead.
        """
        warnings.warn("_store_chunks is deprecated; pipeline stages are handled by PDFCoordinator.", DeprecationWarning, stacklevel=2)
        milvus = get_milvus_service()
        contents = []
        for i, chunk in enumerate(chunks):
            contents.append({
                "paper_id": paper_id,
                "user_id": user_id,
                "content_type": "text",
                "page_num": chunk.get("page_start", 0),
                "section": chunk.get("section", ""),
                "content_data": chunk.get("text", "")[:8000],
                "embedding": embeddings[i],
            })
        milvus.insert_contents_batched(contents)
        logger.debug("Chunks stored", count=len(contents))

    async def _enrich_metadata(self, conn, paper_id: str) -> None:
        """Enrich metadata via S2 API."""
        # Get current paper info
        paper = await conn.fetchrow(
            "SELECT title, authors FROM papers WHERE id = $1",
            paper_id,
        )
        if not paper or not paper["title"]:
            return

        # Try S2 enrichment
        s2_service = get_semantic_scholar_service()
        results = await s2_service.search_papers(
            query=paper["title"],
            limit=5,
        )
        candidates = results.get("data", [])
        if candidates:
            match = fuzzy_match_title(paper["title"], candidates)
            if match:
                await conn.execute(
                    """UPDATE papers
                       SET citations = $1,
                           venue = COALESCE($2, venue),
                           "updatedAt" = NOW()
                       WHERE id = $3""",
                    match.get("citationCount", 0),
                    match.get("venue"),
                    paper_id,
                )
                logger.debug("Metadata enriched", paper_id=paper_id)

    async def _update_graph_relations(self, paper_id: str) -> None:
        """Update Neo4j graph relations."""
        neo4j = Neo4jService()
        # Create paper node (basic graph update)
        async with self.db_pool.acquire() as conn:
            paper = await conn.fetchrow(
                "SELECT title, authors, year FROM papers WHERE id = $1",
                paper_id,
            )
        if paper:
            await neo4j.create_paper_node(
                paper_id=paper_id,
                title=paper["title"] or "Untitled",
                authors=paper["authors"] or [],
                year=paper.get("year"),
            )
            logger.debug("Graph relations updated", paper_id=paper_id)

    async def _calculate_advanced_quality(self, paper_id: str) -> None:
        """Calculate quality score for paper."""
        # Placeholder for quality scoring logic
        # This would typically involve chunk quality analysis
        logger.debug("Quality score calculated", paper_id=paper_id)

    async def enrich_metadata_if_needed(
        self, conn, paper_id: str, title: Optional[str], authors: List[str]
    ) -> bool:
        """Enrich paper metadata using Semantic Scholar.

        Per D-07: Triggered after PDF parsing.
        Per D-08: Only when title or authors missing.
        Per D-09: Fuzzy match with 80% threshold.
        Per D-05: Use S2 API for metadata, avoid LLM costs.

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
            logger.info(
                "Metadata already complete, skipping enrichment", paper_id=paper_id
            )
            return False

        if not title:
            logger.info("No title to search with", paper_id=paper_id)
            return False

        # Per D-05: Use S2 API (NOT LLM) for metadata enrichment
        logger.info(
            "Enriching metadata via Semantic Scholar API (no LLM)",
            paper_id=paper_id,
            title=title[:50],
        )

        try:
            s2_service = get_semantic_scholar_service()

            # Search S2 by title
            logger.info("Searching Semantic Scholar for metadata", title=title[:50])
            search_results = await s2_service.search_papers(
                query=title,
                fields="paperId,title,year,authors,abstract,citationCount,venue,publicationDate",
                limit=5,
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
                    citations = $5,
                    venue = $6,
                    "updatedAt" = NOW()
                WHERE id = $1
                """,
                paper_id,
                enriched_title if enriched_title != title else None,
                enriched_year,
                enriched_abstract,
                citation_count,
                venue,
            )

            logger.info(
                "Paper metadata enriched",
                paper_id=paper_id,
                s2_id=paper_id_s2,
                citations=citation_count,
            )

            return True

        except Exception as e:
            # Per D-09: Don't block PDF processing on enrichment failure
            logger.error("Metadata enrichment failed", paper_id=paper_id, error=str(e))
            return False

    async def process_pdf_task(self, task_id: str) -> bool:
        """
        Process a single PDF task through all stages.

        This method now delegates to PDFCoordinator for parallel processing.
        Maintains backward compatibility with existing code that calls this method.

        Args:
            task_id: UUID of the processing task

        Returns:
            True if successful, False otherwise
        """
        # Ensure coordinator has DB pool
        await self.coordinator.init_db()

        # Delegate to parallel pipeline coordinator
        return await self.coordinator.process(task_id)

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
        self, task_id: str, failures: List[Dict[str, Any]]
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
                task_id,
            )
        logger.info(
            "Stored partial failures", task_id=task_id, failure_count=len(failures)
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

    # Initialize embedding model at startup
    logger.info("Initializing embedding model...")
    try:
        qwen3vl_service = get_qwen3vl_service()
        qwen3vl_service.load_model()
        logger.info("Embedding model initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize embedding model", error=str(e))

    # Initialize Milvus collections at startup
    logger.info("Initializing Milvus collections...")
    try:
        milvus_service = get_milvus_service()
        milvus_service.initialize_collections()
        logger.info("Milvus collections initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Milvus collections", error=str(e))

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
