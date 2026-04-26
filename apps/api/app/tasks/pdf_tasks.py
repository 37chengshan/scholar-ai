"""Celery tasks for PDF processing.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-03: Dynamic concurrency based on memory
Per D-06: Failure isolation (single failure doesn't block batch)
Per D-09: Rate limiting at 120/min for LLM API protection
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import select, func, update, desc

from app.core.celery_config import celery_app
from app.core.worker_async import run_async_in_worker_loop
from app.workers.pdf_worker import PDFProcessor
from app.utils.logger import logger
from app.database import AsyncSessionLocal
from app.models import Paper, ProcessingTask, PaperBatch
from app.models.import_job import ImportJob
from app.models.upload_history import UploadHistory


# Current concurrency level (will be adjusted by memory monitor)
_current_concurrency = 8


def get_current_concurrency() -> int:
    """Get current concurrency level (adjusted by memory monitor)."""
    return _current_concurrency


def set_current_concurrency(value: int):
    """Set current concurrency level (called by memory monitor)."""
    global _current_concurrency
    _current_concurrency = value


_TASK_STAGE_TO_IMPORT_STAGE = {
    # Real PDFCoordinator stages → ImportJob stages
    "downloading": ("resolving_source", 20),
    "parsing": ("parsing", 50),
    "extracting": ("chunking", 70),
    "storing": ("indexing", 85),
    "finalizing": ("finalizing", 95),
}


async def _sync_import_job_stage(
    db,
    processing_task_id: str,
    task_stage: str,
):
    """Mirror ProcessingTask progress into ImportJob when linked by processing_task_id."""
    mapped = _TASK_STAGE_TO_IMPORT_STAGE.get(task_stage)
    if not mapped:
        return

    result = await db.execute(
        select(ImportJob).where(ImportJob.processing_task_id == processing_task_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return

    if job.status in {"completed", "failed", "cancelled"}:
        return

    import_stage, progress = mapped
    job.status = "running"
    job.stage = import_stage
    job.progress = progress
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()


async def _sync_import_job_terminal(
    db,
    processing_task_id: Optional[str],
    terminal_status: str,
    error_message: Optional[str] = None,
):
    """Set ImportJob to terminal status with idempotent guard."""
    if not processing_task_id:
        return

    result = await db.execute(
        select(ImportJob).where(ImportJob.processing_task_id == processing_task_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return

    if job.status in {"completed", "cancelled"}:
        return

    now = datetime.now(timezone.utc)
    if terminal_status == "completed":
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.completed_at = now
        job.next_action = None
    else:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = "PROCESSING_FAILED"
        job.error_message = error_message or "Processing failed"
        job.next_action = {"type": "retry", "message": job.error_message}

    if job.paper_id:
        history_result = await db.execute(
            select(UploadHistory)
            .where(
                UploadHistory.user_id == job.user_id,
                UploadHistory.paper_id == job.paper_id,
            )
            .order_by(desc(UploadHistory.created_at))
            .limit(1)
        )
        history = history_result.scalars().first()
        if history:
            history.status = "COMPLETED" if terminal_status == "completed" else "FAILED"
            history.error_message = None if terminal_status == "completed" else (error_message or history.error_message)
            history.updated_at = now
        else:
            db.add(
                UploadHistory(
                    user_id=job.user_id,
                    paper_id=job.paper_id,
                    filename=job.filename or job.source_ref_raw or "untitled.pdf",
                    status="COMPLETED" if terminal_status == "completed" else "FAILED",
                    error_message=None if terminal_status == "completed" else error_message,
                    created_at=now,
                    updated_at=now,
                )
            )

    job.updated_at = now
    await db.commit()


@celery_app.task(bind=True, rate_limit='120/m')
def process_pdf_batch_task(self, batch_id: str):
    """
    Process batch of PDFs with concurrent execution.

    Per D-03: Dynamic concurrency based on memory
    Per D-06: Failure isolation (single failure doesn't block batch)
    """

    async def _process_batch():
        async with AsyncSessionLocal() as db:
            # Query papers for this batch (only uploaded ones)
            result = await db.execute(
                select(Paper.id).where(
                    Paper.batch_id == batch_id,
                    Paper.upload_status == 'completed'
                )
            )
            papers = result.scalars().all()

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
            completed_result = await db.execute(
                select(func.count()).select_from(Paper).where(
                    Paper.batch_id == batch_id,
                    Paper.status == 'completed'
                )
            )
            completed = completed_result.scalar() or 0

            failed_result = await db.execute(
                select(func.count()).select_from(Paper).where(
                    Paper.batch_id == batch_id,
                    Paper.status == 'failed'
                )
            )
            failed = failed_result.scalar() or 0

            status = 'completed' if failed == 0 else 'partial_failure'
            await db.execute(
                update(PaperBatch).where(PaperBatch.id == batch_id).values(status=status)
            )
            await db.commit()

            logger.info(f"Batch {batch_id} complete: {completed} success, {failed} failed")

    # Run async function in sync Celery task
    run_async_in_worker_loop(_process_batch())


async def process_single_pdf_async(
    paper_id: str,
    celery_task,
    processing_task_id: Optional[str] = None,
):
    """
    Process single PDF with progress updates.

    Reuses PDFProcessor from pdf_worker.py.
    Updates Celery task state for progress tracking.
    """
    processor = PDFProcessor()
    task_id: Optional[str] = processing_task_id

    async with AsyncSessionLocal() as db:
        try:
            # Check if task already exists
            if processing_task_id:
                result = await db.execute(
                    select(ProcessingTask).where(ProcessingTask.id == processing_task_id)
                )
            else:
                result = await db.execute(
                    select(ProcessingTask).where(ProcessingTask.paper_id == paper_id)
                )
            existing_task = result.scalar_one_or_none()

            if existing_task:
                task_id = existing_task.id
                storage_key = existing_task.storage_key
                # Update status to processing
                existing_task.status = 'processing'
                existing_task.updated_at = datetime.now(timezone.utc)
            else:
                # Create new task record with UUID
                task_id = processing_task_id or str(uuid.uuid4())
                # Get storage_key from papers table
                paper_result = await db.execute(
                    select(Paper.storage_key).where(Paper.id == paper_id)
                )
                storage_key = paper_result.scalar_one_or_none()

                new_task = ProcessingTask(
                    id=task_id,
                    paper_id=paper_id,
                    status='processing',
                    storage_key=storage_key or '',
                )
                db.add(new_task)

            await db.commit()

            # Delegate entirely to PDFProcessor → PDFCoordinator.
            # ProcessingTask stage updates come from the real pipeline; no fake loop here.
            celery_task.update_state(
                state='PROGRESS',
                meta={'paper_id': paper_id, 'stage': 'processing', 'progress': 10},
            )
            success = await processor.process_pdf_task(task_id)

            if success:
                await db.execute(
                    update(ProcessingTask).where(ProcessingTask.id == task_id).values(
                        status='completed',
                        completed_at=datetime.now(timezone.utc)
                    )
                )
                await db.execute(
                    update(Paper).where(Paper.id == paper_id).values(status='completed')
                )
                await db.commit()
                await _sync_import_job_terminal(db, task_id, "completed")

                # Backward-compatible fallback callback.
                try:
                    from app.workers.import_worker import on_processing_task_complete
                    on_processing_task_complete.delay(task_id, paper_id)
                except Exception as callback_error:
                    logger.warning(
                        "Failed to enqueue import completion callback",
                        processing_task_id=task_id,
                        paper_id=paper_id,
                        error=str(callback_error),
                    )

                celery_task.update_state(
                    state='COMPLETED',
                    meta={'paper_id': paper_id, 'progress': 100}
                )
            else:
                raise Exception("PDF processing failed")

        except Exception as e:
            logger.error(f"Failed to process paper {paper_id}: {e}")

            # Record error details (per D-08)
            # Note: error_stage and error_time fields not in current ProcessingTask model
            # Storing error info in error_message with context
            error_detail = f"[stage: processing] {str(e)}"
            if task_id:
                await db.execute(
                    update(ProcessingTask).where(ProcessingTask.id == task_id).values(
                        error_message=error_detail,
                        status='failed'
                    )
                )
            else:
                await db.execute(
                    update(ProcessingTask).where(ProcessingTask.paper_id == paper_id).values(
                        error_message=error_detail,
                        status='failed'
                    )
                )
            await db.execute(
                update(Paper).where(Paper.id == paper_id).values(status='failed')
            )
            await db.commit()
            await _sync_import_job_terminal(db, task_id, "failed", error_detail)

            raise


@celery_app.task(
    bind=True,
    rate_limit='120/m',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_single_pdf_task(self, paper_id: str, processing_task_id: Optional[str] = None):
    """Standalone task to process single PDF (used for retry)."""
    run_async_in_worker_loop(process_single_pdf_async(paper_id, self, processing_task_id))


@celery_app.task
def retry_batch_failed_papers_task(batch_id: str):
    """Retry all failed papers in a batch."""

    async def _retry_failed():
        async with AsyncSessionLocal() as db:
            # Find failed papers
            result = await db.execute(
                select(Paper.id).where(
                    Paper.batch_id == batch_id,
                    Paper.status == 'failed'
                )
            )
            failed_papers = result.scalars().all()

            logger.info(f"Retrying {len(failed_papers)} failed papers in batch {batch_id}")

            # Trigger retry for each
            for paper_id in failed_papers:
                process_single_pdf_task.delay(paper_id)

    run_async_in_worker_loop(_retry_failed())
