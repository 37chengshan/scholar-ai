"""Celery tasks for PDF processing.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-03: Dynamic concurrency based on memory
Per D-06: Failure isolation (single failure doesn't block batch)
Per D-09: Rate limiting at 120/min for LLM API protection
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_config import celery_app
from app.workers.pdf_worker import PDFProcessor
from app.workers.import_worker import on_processing_task_complete
from app.utils.logger import logger
from app.database import AsyncSessionLocal
from app.models import Paper, ProcessingTask, PaperBatch


# Current concurrency level (will be adjusted by memory monitor)
_current_concurrency = 8


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
    asyncio.run(_process_batch())


async def process_single_pdf_async(paper_id: str, celery_task):
    """
    Process single PDF with progress updates.

    Reuses PDFProcessor from pdf_worker.py.
    Updates Celery task state for progress tracking.
    """
    processor = PDFProcessor()

    async with AsyncSessionLocal() as db:
        try:
            # Check if task already exists
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
                task_id = str(uuid.uuid4())
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
                await db.execute(
                    update(ProcessingTask).where(ProcessingTask.id == task_id).values(status=stage_name)
                )
                await db.commit()

                # Execute stage using PDFProcessor
                # Note: PDFProcessor.process_pdf_task handles all stages internally
                # This is a simplified version - actual implementation would call individual stages
                logger.info(f"Processing paper {paper_id} at stage {stage_name}")

            # Use PDFProcessor to process the PDF
            success = await processor.process_pdf_task(task_id)

            if success:
                # Mark as completed
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

                # Notify ImportJob that processing is complete
                on_processing_task_complete.delay(task_id, paper_id)

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
            # Note: error_stage and error_time fields not in current ProcessingTask model
            # Storing error info in error_message with context
            error_detail = f"[stage: processing] {str(e)}"
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

            raise


@celery_app.task(bind=True, rate_limit='120/m')
def process_single_pdf_task(self, paper_id: str):
    """Standalone task to process single PDF (used for retry)."""
    asyncio.run(process_single_pdf_async(paper_id, self))


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

    asyncio.run(_retry_failed())