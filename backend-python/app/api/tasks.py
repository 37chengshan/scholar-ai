"""Task management endpoints for triggering Celery tasks.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-07: Manual retry by user
Per D-02: Auto-start batch processing when all files uploaded
"""

from fastapi import APIRouter, HTTPException
from app.tasks.pdf_tasks import (
    process_single_pdf_task,
    retry_batch_failed_papers_task,
    process_pdf_batch_task,
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post("/retry/{paper_id}")
async def retry_single_paper(paper_id: str):
    """
    Trigger Celery task to retry a single failed paper.

    Per D-07: Manual retry by user
    """
    try:
        # Trigger async task
        process_single_pdf_task.delay(paper_id)
        logger.info(f"Triggered retry task for paper {paper_id}")

        return {"success": True, "paper_id": paper_id}
    except Exception as e:
        logger.error(f"Failed to trigger retry for paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-batch/{batch_id}")
async def retry_batch(batch_id: str):
    """
    Trigger Celery task to retry all failed papers in a batch.

    Per D-07: Batch retry for all failed papers
    """
    try:
        # Trigger async task
        retry_batch_failed_papers_task.delay(batch_id)
        logger.info(f"Triggered batch retry task for batch {batch_id}")

        return {"success": True, "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Failed to trigger batch retry for batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-batch/{batch_id}")
async def trigger_batch_processing(batch_id: str):
    """
    Trigger Celery task to process all papers in a batch.

    Per D-02: Auto-start processing when all files uploaded
    """
    try:
        # Trigger async batch task
        process_pdf_batch_task.delay(batch_id)
        logger.info(f"Triggered batch processing task for batch {batch_id}")

        return {"success": True, "batch_id": batch_id, "status": "processing"}
    except Exception as e:
        logger.error(f"Failed to trigger batch processing for batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))