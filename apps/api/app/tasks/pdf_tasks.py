"""Celery tasks for PDF processing.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-03: Dynamic concurrency based on memory
Per D-06: Failure isolation (single failure doesn't block batch)
Per D-09: Rate limiting at 120/min for LLM API protection
"""

import asyncio
import os
import uuid

import asyncpg

from app.core.celery_config import celery_app
from app.workers.pdf_worker import PDFProcessor
from app.workers.import_worker import on_processing_task_complete
from app.utils.logger import logger


# Current concurrency level (will be adjusted by memory monitor)
_current_concurrency = 8


def _get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://scholarai:scholarai123@localhost:5432/scholarai",
    )


def get_current_concurrency() -> int:
    """Get current concurrency level (adjusted by memory monitor)."""
    return _current_concurrency


def set_current_concurrency(value: int):
    """Set current concurrency level (called by memory monitor)."""
    global _current_concurrency
    _current_concurrency = value


@celery_app.task(bind=True, rate_limit='120/m')
def process_pdf_batch_task(self, batch_id: str):
    """
    Process batch of PDFs with concurrent execution.

    Per D-03: Dynamic concurrency based on memory
    Per D-06: Failure isolation (single failure doesn't block batch)
    """

    async def _process_batch():
        conn = await asyncpg.connect(_get_database_url())
        try:
            # Query papers for this batch (only uploaded ones)
            rows = await conn.fetch(
                """SELECT id FROM papers
                   WHERE batch_id = $1 AND upload_status = 'completed'""",
                batch_id,
            )
            papers = [r['id'] for r in rows]

            if not papers:
                logger.info(f"No uploaded papers found for batch {batch_id}")
                return

            # Get dynamic concurrency
            concurrency = get_current_concurrency()
            semaphore = asyncio.Semaphore(concurrency)

            logger.info(f"Processing batch {batch_id} with {len(papers)} papers, concurrency={concurrency}")

            async def process_with_semaphore(paper_id: str):
                """Process single PDF with semaphore limit."""
                async with semaphore:
                    try:
                        await process_single_pdf_async(paper_id, self)
                    except Exception as e:
                        # Log error but don't raise - failure isolation (D-06)
                        logger.error(f"Paper {paper_id} failed: {e}")
                        # Error already recorded in process_single_pdf_async

            # Process all papers concurrently with failure isolation
            tasks = [process_with_semaphore(paper_id) for paper_id in papers]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Update batch status
            completed = await conn.fetchval(
                """SELECT COUNT(*) FROM papers
                   WHERE batch_id = $1 AND status = 'completed'""",
                batch_id,
            ) or 0

            failed = await conn.fetchval(
                """SELECT COUNT(*) FROM papers
                   WHERE batch_id = $1 AND status = 'failed'""",
                batch_id,
            ) or 0

            status = 'completed' if failed == 0 else 'partial_failure'
            await conn.execute(
                """UPDATE paper_batches SET status = $1 WHERE id = $2""",
                status,
                batch_id,
            )

            logger.info(f"Batch {batch_id} complete: {completed} success, {failed} failed")
        finally:
            await conn.close()

    # Run async function in sync Celery task
    asyncio.run(_process_batch())


async def process_single_pdf_async(paper_id: str, celery_task):
    """
    Process single PDF with progress updates.

    Reuses PDFProcessor from pdf_worker.py.
    Updates Celery task state for progress tracking.
    """
    processor = PDFProcessor()
    conn = await asyncpg.connect(_get_database_url())

    try:
        existing_task = await conn.fetchrow(
            """SELECT id, storage_key
               FROM processing_tasks
               WHERE paper_id = $1
               ORDER BY created_at DESC NULLS LAST, updated_at DESC NULLS LAST
               LIMIT 1""",
            paper_id,
        )

        if existing_task:
            task_id = existing_task["id"]
            storage_key = existing_task["storage_key"]
            await conn.execute(
                """UPDATE processing_tasks
                   SET status = 'processing',
                       updated_at = NOW(),
                       error_message = NULL
                   WHERE id = $1""",
                task_id,
            )
        else:
            task_id = str(uuid.uuid4())
            storage_key = await conn.fetchval(
                'SELECT storage_key FROM papers WHERE id = $1',
                paper_id,
            )
            await conn.execute(
                """INSERT INTO processing_tasks (id, paper_id, status, storage_key)
                   VALUES ($1, $2, 'processing', $3)""",
                task_id,
                paper_id,
                storage_key or '',
            )

        stages = [
            ('processing_ocr', 15),
            ('parsing', 30),
            ('extracting_imrad', 45),
            ('generating_notes', 60),
            ('storing_vectors', 75),
            ('indexing_multimodal', 90),
        ]

        for stage_name, progress in stages:
            celery_task.update_state(
                state='PROGRESS',
                meta={
                    'paper_id': paper_id,
                    'stage': stage_name,
                    'progress': progress
                }
            )
            await conn.execute(
                """UPDATE processing_tasks
                   SET status = $1,
                       updated_at = NOW()
                   WHERE id = $2""",
                stage_name,
                task_id,
            )
            logger.info(f"Processing paper {paper_id} at stage {stage_name}")

        success = await processor.process_pdf_task(task_id)

        if success:
            await conn.execute(
                """UPDATE processing_tasks
                   SET status = 'completed',
                       completed_at = NOW(),
                       updated_at = NOW()
                   WHERE id = $1""",
                task_id,
            )
            await conn.execute(
                """UPDATE papers
                   SET status = 'completed',
                       "updatedAt" = NOW()
                   WHERE id = $1""",
                paper_id,
            )
            on_processing_task_complete.delay(task_id, paper_id)
            celery_task.update_state(
                state='COMPLETED',
                meta={'paper_id': paper_id, 'progress': 100}
            )
        else:
            raise Exception("PDF processing failed")

    except Exception as e:
        logger.error(f"Failed to process paper {paper_id}: {e}")
        error_detail = f"[stage: processing] {str(e)}"
        await conn.execute(
            """UPDATE processing_tasks
               SET error_message = $1,
                   status = 'failed',
                   updated_at = NOW()
               WHERE paper_id = $2""",
            error_detail,
            paper_id,
        )
        await conn.execute(
            """UPDATE papers
               SET status = 'failed',
                   "updatedAt" = NOW()
               WHERE id = $1""",
            paper_id,
        )
        raise
    finally:
        await conn.close()


@celery_app.task(bind=True, rate_limit='120/m')
def process_single_pdf_task(self, paper_id: str):
    """Standalone task to process single PDF (used for retry)."""
    asyncio.run(process_single_pdf_async(paper_id, self))


@celery_app.task
def retry_batch_failed_papers_task(batch_id: str):
    """Retry all failed papers in a batch."""

    async def _retry_failed():
        conn = await asyncpg.connect(_get_database_url())
        try:
            # Find failed papers
            rows = await conn.fetch(
                """SELECT id FROM papers
                   WHERE batch_id = $1 AND status = 'failed'""",
                batch_id,
            )
            failed_papers = [r['id'] for r in rows]

            logger.info(f"Retrying {len(failed_papers)} failed papers in batch {batch_id}")

            # Trigger retry for each
            for paper_id in failed_papers:
                process_single_pdf_task.delay(paper_id)
        finally:
            await conn.close()

    asyncio.run(_retry_failed())
