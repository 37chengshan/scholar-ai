"""PDF processing coordinator for parallel pipeline execution.

Orchestrates the PDF processing pipeline through:
1. Download stage (DownloadManager)
2. Parsing stage (ParsingManager)
3. Parallel extraction stage (ExtractionPipeline)
4. Storage stage (StorageManager)

Per D-01: Complete refactor from serial to parallel architecture.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Optional

import asyncpg

from app.workers.pipeline_context import PipelineContext, PipelineStage
from app.workers.extraction_pipeline import ExtractionPipeline, PipelineError
from app.core.storage import ObjectStorage
from app.core.docling_service import DoclingParser
from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.milvus_service import get_milvus_service
from app.core.image_extractor import ImageExtractor
from app.core.table_extractor import TableExtractor
from app.core.multimodal_indexer import get_multimodal_indexer
from app.utils.logger import logger


class PDFCoordinator:
    """PDF processing pipeline coordinator.

    Coordinates parallel execution of extraction tasks while
    maintaining strict error handling per D-12, D-13, D-14.

    Per D-04: Four-stage parallel extraction (IMRaD, metadata, images, tables).
    Per D-07: ThreadPoolExecutor with max_workers=4 for CPU-intensive tasks.
    """

    def __init__(self):
        """Initialize coordinator with required services.

        Matches existing PDFProcessor initialization for compatibility.
        """
        self.storage = ObjectStorage()
        self.parser = DoclingParser()
        self.extraction_pipeline = ExtractionPipeline(max_workers=4)  # Per D-07
        self.embedding_service = get_qwen3vl_service()
        self.neo4j_service = Neo4jService()
        self.notes_generator = NotesGenerator()
        self.milvus_service = get_milvus_service()
        self.image_extractor = ImageExtractor()
        self.table_extractor = TableExtractor()
        self.multimodal_indexer = None  # Lazy init
        self.db_pool: Optional[asyncpg.Pool] = None

    async def init_db(self) -> None:
        """Initialize database connection pool.

        Uses asyncpg pool with min_size=1, max_size=10.
        Lazy initialization on first use.
        """
        if not self.db_pool:
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://scholarai:scholarai123@localhost:5432/scholarai"
            )
            self.db_pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10
            )

    async def process(self, task_id: str) -> bool:
        """Process a PDF task through the parallel pipeline.

        Main entry point for PDF processing. Coordinates all stages.

        Args:
            task_id: UUID of the processing task

        Returns:
            True if successful, False otherwise

        Pipeline stages:
        1. DOWNLOAD - Retrieve PDF from object storage
        2. PARSING - Docling OCR + parsing (10s bottleneck)
        3. EXTRACTION - Parallel IMRaD, metadata, images, tables
        4. STORAGE - Batch storage to PostgreSQL, Milvus, Neo4j
        """
        await self.init_db()

        # Initialize context
        ctx = await self._init_context(task_id)

        try:
            # Stage 1: Download
            ctx.current_stage = PipelineStage.DOWNLOAD
            try:
                # Create temp file for PDF download
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    await self.storage.download_file(ctx.storage_key, tmp.name)
                    ctx.local_path = tmp.name
                logger.info(f"Downloaded PDF to {ctx.local_path} for task {ctx.task_id}")
            except Exception as e:
                ctx.errors.append(f"Download failed: {str(e)}")
                await self._update_status(ctx, PipelineStage.FAILED.value, error=str(e))
                raise PipelineError(f"Download stage failed: {e}")

            # Stage 2: Parsing
            ctx.current_stage = PipelineStage.PARSING
            try:
                ctx.parse_result = await self.parser.parse_pdf(ctx.local_path)
                logger.info(
                    f"Parsed PDF for task {ctx.task_id}: "
                    f"{len(ctx.parse_result.get('pages', []))} pages"
                )
            except Exception as e:
                ctx.errors.append(f"Parsing failed: {str(e)}")
                await self._update_status(ctx, PipelineStage.FAILED.value, error=str(e))
                raise PipelineError(f"Parsing stage failed: {e}")

            # Stage 3: Parallel extraction
            ctx.current_stage = PipelineStage.EXTRACTION
            ctx = await self.extraction_pipeline.extract(ctx)
            logger.info(f"Completed parallel extraction for task {ctx.task_id}")

            # Stage 4: Storage (to be implemented in Plan 03)
            ctx.current_stage = PipelineStage.STORAGE
            # TODO: await self.storage_manager.store(ctx)

            ctx.current_stage = PipelineStage.COMPLETED
            await self._update_status(ctx, "completed")
            return True

        except Exception as e:
            ctx.add_error(str(e))
            ctx.current_stage = PipelineStage.FAILED
            await self._update_status(ctx, "failed", error=str(e))
            logger.error("Pipeline failed", task_id=task_id, error=str(e))
            return False

    async def _init_context(self, task_id: str) -> PipelineContext:
        """Initialize pipeline context from task database record.

        Loads task metadata from processing_tasks and papers tables.

        Args:
            task_id: UUID of the processing task

        Returns:
            PipelineContext with task metadata

        Raises:
            ValueError: If task not found
        """
        async with self.db_pool.acquire() as conn:
            task = await conn.fetchrow(
                """SELECT pt.*, p.user_id, p.id as paper_id, p.storage_key
                   FROM processing_tasks pt
                   JOIN papers p ON pt.paper_id = p.id
                   WHERE pt.id = $1""",
                task_id
            )

        if not task:
            raise ValueError(f"Task not found: {task_id}")

        return PipelineContext(
            task_id=task_id,
            paper_id=task["paper_id"],
            user_id=task["user_id"],
            storage_key=task["storage_key"]
        )

    async def _update_status(
        self,
        ctx: PipelineContext,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Update task status in database.

        Matches existing PDFProcessor._update_status implementation.

        Args:
            ctx: Pipeline context with task_id
            status: New status string
            error: Optional error message for failures
        """
        async with self.db_pool.acquire() as conn:
            completed_at = datetime.now() if status == "completed" else None

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
                ctx.task_id
            )

        logger.info("Task status updated", task_id=ctx.task_id, status=status)


# Singleton pattern for coordinator
_coordinator: Optional[PDFCoordinator] = None


def get_pdf_coordinator() -> PDFCoordinator:
    """Get or create PDFCoordinator singleton.

    Singleton pattern for service reuse across tasks.

    Returns:
        PDFCoordinator instance
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = PDFCoordinator()
    return _coordinator