"""Batch Import API endpoints.

Per gpt意见.md Section 2.1.2: POST /knowledge-bases/{kb_id}/imports/batch
Per gpt意见.md Section 2.4.3: GET /import-batches/{batch_id}

Endpoints:
- POST /knowledge-bases/{kb_id}/imports/batch - Create batch import
- GET /import-batches/{batch_id} - Get batch status with aggregate counts
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.models.knowledge_base import KnowledgeBase
from app.models.import_batch import ImportBatch
from app.models.import_job import ImportJob
from app.services.import_job_service import ImportJobService
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints per D-36-02-03."""

    success: bool = True
    data: Dict[str, Any]


class BatchImportItem(BaseModel):
    """Single item in batch import request."""

    sourceType: str  # local_file, arxiv, pdf_url, doi, semantic_scholar
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific payload (filename for local_file, input for external)",
    )


class BatchImportRequest(BaseModel):
    """Request to create multiple ImportJobs in batch."""

    items: List[BatchImportItem] = Field(min_length=1, max_length=50)
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Import options (dedupePolicy, autoAttachToKb)"
    )


class BatchItemResponse(BaseModel):
    """Response for single batch item."""

    importJobId: str
    sourceType: str
    status: str
    nextAction: Optional[Dict[str, Any]] = None


class BatchSummary(BaseModel):
    """Aggregate summary for batch status."""

    total: int
    running: int
    completed: int
    failed: int
    cancelled: int


# =============================================================================
# Create Batch Import Endpoint
# =============================================================================


@router.post("/knowledge-bases/{kb_id}/imports/batch", response_model=KBResponse)
async def create_batch_import(
    kb_id: str,
    request: BatchImportRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple ImportJobs in batch.

    Per gpt意见.md 2.1.2: Returns batchJobId and individual job statuses.

    Args:
        kb_id: Knowledge base ID
        request: Batch import request with items and options
        user_id: Current user ID
        db: Database session

    Returns:
        KBResponse with batchJobId and items list
    """
    try:
        # Validate KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Limit batch size
        if len(request.items) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Maximum 50 items per batch"),
            )

        # Create ImportBatch record
        batch_id = f"impb_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        batch = ImportBatch(
            id=batch_id,
            user_id=user_id,
            knowledge_base_id=kb_id,
            status="created",
            total_items=len(request.items),
            completed_items=0,
            failed_items=0,
            cancelled_items=0,
            created_at=now,
            updated_at=now,
        )
        db.add(batch)

        # Create individual ImportJobs
        service = ImportJobService()
        items_response: List[Dict[str, Any]] = []

        for item in request.items:
            # Extract source_ref_raw from payload
            if item.sourceType == "local_file":
                source_ref_raw = item.payload.get("filename", "unnamed.pdf")
            else:
                source_ref_raw = item.payload.get("input", "")

            # Create job with batch_id linkage
            job = await service.create_job(
                user_id=user_id,
                kb_id=kb_id,
                source_type=item.sourceType,
                source_ref_raw=source_ref_raw,
                options=request.options or {},
                batch_id=batch_id,  # Link to batch
                db=db,
            )

            items_response.append({
                "importJobId": job.id,
                "sourceType": item.sourceType,
                "status": job.status,
                "nextAction": job.next_action if item.sourceType == "local_file" else None,
            })

        await db.commit()

        logger.info(
            "Batch import created",
            batch_id=batch_id,
            kb_id=kb_id,
            total_items=len(request.items),
        )

        return KBResponse(
            success=True,
            data={
                "batchJobId": batch_id,
                "status": "created",
                "totalItems": len(request.items),
                "items": items_response,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create batch import", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create batch import: {str(e)}"),
        )


# =============================================================================
# Get Batch Status Endpoint
# =============================================================================


@router.get("/import-batches/{batch_id}", response_model=KBResponse)
async def get_batch_status(
    batch_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get batch import aggregate status.

    Per gpt意见.md 2.4.3: Returns summary with counts and individual job status.

    Args:
        batch_id: ImportBatch ID
        user_id: Current user ID
        db: Database session

    Returns:
        KBResponse with batch status, summary counts, and items list
    """
    try:
        # Get batch with ownership check
        batch_result = await db.execute(
            select(ImportBatch).where(
                ImportBatch.id == batch_id, ImportBatch.user_id == user_id
            )
        )
        batch = batch_result.scalar_one_or_none()

        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Batch not found"),
            )

        # Query all jobs in batch
        jobs_result = await db.execute(
            select(ImportJob).where(ImportJob.batch_id == batch_id)
        )
        jobs = jobs_result.scalars().all()

        # Build items list
        items = [
            {
                "importJobId": j.id,
                "title": j.resolved_title,
                "status": j.status,
                "stage": j.stage,
                "progress": j.progress,
            }
            for j in jobs
        ]

        # Update batch counts
        batch.completed_items = sum(1 for j in jobs if j.status == "completed")
        batch.failed_items = sum(1 for j in jobs if j.status == "failed")
        batch.cancelled_items = sum(1 for j in jobs if j.status == "cancelled")

        # Determine batch status
        if batch.completed_items == batch.total_items:
            batch.status = "completed"
        elif batch.failed_items == batch.total_items:
            batch.status = "failed"
        elif batch.cancelled_items == batch.total_items:
            batch.status = "cancelled"
        elif batch.failed_items > 0 or batch.cancelled_items > 0:
            batch.status = "partial"
        else:
            batch.status = "running"

        batch.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return KBResponse(
            success=True,
            data={
                "batchJobId": batch_id,
                "status": batch.status,
                "summary": {
                    "total": batch.total_items,
                    "running": sum(1 for j in jobs if j.status in ["running", "queued", "created"]),
                    "completed": batch.completed_items,
                    "failed": batch.failed_items,
                    "cancelled": batch.cancelled_items,
                },
                "items": items,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get batch status", error=str(e), batch_id=batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get batch status: {str(e)}"),
        )


__all__ = ["router"]