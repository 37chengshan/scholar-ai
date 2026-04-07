"""Celery tasks for PDF processing.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-03: Dynamic concurrency based on memory
Per D-06: Failure isolation (single failure doesn't block batch)
Per D-09: Rate limiting at 120/min for LLM API protection
"""

import asyncio
from typing import Dict, Any

from app.core.celery_config import celery_app
from app.workers.pdf_worker import PDFProcessor
from app.utils.logger import logger
from app.core.database import postgres_db


# Current concurrency level (will be adjusted by memory monitor)
_current_concurrency = 8


def get_current_concurrency() -> int:
    """Get current concurrency level (adjusted by memory monitor)."""
    return _current_concurrency


def set_current_concurrency(value: int):
    """Set current concurrency level (called by memory monitor)."""
    global _current_concurrency
    _current_concurrency = value


async def get_db_pool():
    """Get database connection pool."""
    if not postgres_db.pool:
        await postgres_db.connect()
    return postgres_db.pool


@celery_app.task(bind=True, rate_limit='120/m')
def process_pdf_batch_task(self, batch_id: str):
    """
    Process batch of PDFs with concurrent execution.

    Per D-03: Dynamic concurrency based on memory
    Per D-06: Failure isolation (single failure doesn't block batch)
    """

    async def _process_batch():
        pool = await get_db_pool()

        # Query papers for this batch (only uploaded ones)
        papers = await pool.fetch(
            """SELECT id FROM papers
               WHERE batch_id = $1 AND upload_status = 'completed'""",
            batch_id
        )

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
        tasks = [process_with_semaphore(paper['id']) for paper in papers]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Update batch status
        completed = await pool.fetchval(
            """SELECT COUNT(*) FROM papers
               WHERE batch_id = $1 AND status = 'completed'""",
            batch_id
        )
        failed = await pool.fetchval(
            """SELECT COUNT(*) FROM papers
               WHERE batch_id = $1 AND status = 'failed'""",
            batch_id
        )

        status = 'completed' if failed == 0 else 'partial_failure'
        await pool.execute(
            "UPDATE paper_batches SET status = $1 WHERE id = $2",
            status, batch_id
        )

        logger.info(f"Batch {batch_id} complete: {completed} success, {failed} failed")

    # Run async function in sync Celery task
    asyncio.run(_process_batch())


async def process_single_pdf_async(paper_id: str, celery_task):
    """
    Process single PDF with progress updates.

    Reuses PDFProcessor from pdf_worker.py.
    Updates Celery task state for progress tracking.
    """
    processor = PDFProcessor()

    try:
        pool = await get_db_pool()
        
        # Check if task already exists
        existing_task = await pool.fetchrow(
            "SELECT id, storage_key FROM processing_tasks WHERE paper_id = $1",
            paper_id
        )
        
        if existing_task:
            task_id = existing_task['id']
            storage_key = existing_task['storage_key']
            # Update status to processing
            await pool.execute(
                "UPDATE processing_tasks SET status = 'processing', updated_at = NOW() WHERE id = $1",
                task_id
            )
        else:
            # Create new task record with UUID
            import uuid
            task_id = str(uuid.uuid4())
            # Get storage_key from papers table
            paper = await pool.fetchrow(
                "SELECT storage_key FROM papers WHERE id = $1",
                paper_id
            )
            storage_key = paper['storage_key'] if paper else None
            
            await pool.execute(
                """INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
                   VALUES ($1, $2, 'processing', $3, NOW(), NOW())""",
                task_id, paper_id, storage_key
            )

        # Processing stages with progress percentages (per D-05)
        stages = [
            ('processing_ocr', 15),
            ('parsing', 30),
            ('extracting_imrad', 45),
            ('generating_notes', 60),
            ('storing_vectors', 75),
            ('indexing_multimodal', 90),
        ]

        # Execute stages
        for stage_name, progress in stages:
            # Update Celery state for progress tracking
            celery_task.update_state(
                state='PROGRESS',
                meta={
                    'paper_id': paper_id,
                    'stage': stage_name,
                    'progress': progress
                }
            )

            # Update processing_task status
            await pool.execute(
                "UPDATE processing_tasks SET status = $1 WHERE id = $2",
                stage_name, task_id
            )

            # Execute stage using PDFProcessor
            # Note: PDFProcessor.process_pdf_task handles all stages internally
            # This is a simplified version - actual implementation would call individual stages
            logger.info(f"Processing paper {paper_id} at stage {stage_name}")

        # Use PDFProcessor to process the PDF
        success = await processor.process_pdf_task(task_id)

        if success:
            # Mark as completed
            await pool.execute(
                "UPDATE processing_tasks SET status = 'completed' WHERE id = $1",
                task_id
            )
            await pool.execute(
                "UPDATE papers SET status = 'completed' WHERE id = $1",
                paper_id
            )

            # Update Celery state
            celery_task.update_state(
                state='COMPLETED',
                meta={'paper_id': paper_id, 'progress': 100}
            )
        else:
            raise Exception("PDF processing failed")

    except Exception as e:
        logger.error(f"Failed to process paper {paper_id}: {e}")

        # Record error details (per D-08)
        await pool.execute(
            """UPDATE processing_tasks
               SET error_message = $1,
                   error_stage = $2,
                   error_time = NOW(),
                   status = 'failed'
               WHERE paper_id = $3""",
            str(e), 'processing', paper_id
        )
        await pool.execute(
            "UPDATE papers SET status = 'failed' WHERE id = $1",
            paper_id
        )

        raise


@celery_app.task(bind=True, rate_limit='120/m')
def process_single_pdf_task(self, paper_id: str):
    """Standalone task to process single PDF (used for retry)."""
    asyncio.run(process_single_pdf_async(paper_id, self))


@celery_app.task
def retry_batch_failed_papers_task(batch_id: str):
    """Retry all failed papers in a batch."""

    async def _retry_failed():
        pool = await get_db_pool()

        # Find failed papers
        failed_papers = await pool.fetch(
            """SELECT id FROM papers
               WHERE batch_id = $1 AND status = 'failed'""",
            batch_id
        )

        logger.info(f"Retrying {len(failed_papers)} failed papers in batch {batch_id}")

        # Trigger retry for each
        for paper in failed_papers:
            process_single_pdf_task.delay(paper['id'])

    asyncio.run(_retry_failed())