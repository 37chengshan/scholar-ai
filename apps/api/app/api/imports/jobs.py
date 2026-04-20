"""ImportJob API endpoints.

Per D-01: ImportJob-first pattern - create ImportJob before Paper entity.
Per D-03: Wave 1 only - local file upload + get/list endpoints.
Per D-08: State machine with status/stage/progress tracking.

Endpoints:
- POST /knowledge-bases/{kb_id}/imports - Create ImportJob
- PUT /import-jobs/{job_id}/file - Upload PDF to ImportJob
- GET /import-jobs/{job_id} - Get ImportJob status with next_action
- GET /import-jobs - List ImportJobs for user
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.models.knowledge_base import KnowledgeBase
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


class CreateImportRequest(BaseModel):
    """Request to create an ImportJob."""

    sourceType: Literal["local_file", "arxiv", "pdf_url", "doi", "semantic_scholar"]
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific payload (filename for local_file, input for external)",
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Import options (autoAttachToKb, dedupePolicy, etc.)"
    )


# =============================================================================
# Create ImportJob Endpoint
# =============================================================================


@router.post("/knowledge-bases/{kb_id}/imports", response_model=KBResponse)
async def create_import_job(
    kb_id: str,
    request: CreateImportRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Create ImportJob. Per D-01: Job created before Paper entity.

    For local_file: returns next_action with upload_url.
    For external sources: starts in queued state for worker processing.
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
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Extract source_ref_raw from payload
        if request.sourceType == "local_file":
            source_ref_raw = request.payload.get("filename", "unnamed.pdf")
        else:
            source_ref_raw = request.payload.get("input", "")

        # Create job
        service = ImportJobService()
        job = await service.create_job(
            user_id=user_id,
            kb_id=kb_id,
            source_type=request.sourceType,
            source_ref_raw=source_ref_raw,
            options=request.options or {},
            db=db,
        )

        return KBResponse(
            success=True,
            data={
                "importJobId": job.id,
                "knowledgeBaseId": kb_id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "nextAction": job.next_action,
                "preview": {
                    "title": None,
                    "authors": [],
                    "year": None,
                    "sourceLabel": request.sourceType,
                },
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=Errors.validation(str(e)),
        )
    except Exception as e:
        logger.error("Failed to create ImportJob", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create import job: {str(e)}"),
        )


# =============================================================================
# Upload File Endpoint
# =============================================================================


@router.put("/import-jobs/{job_id}/file", response_model=KBResponse)
async def upload_file_to_job(
    job_id: str,
    file: UploadFile = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload PDF to ImportJob (fallback/small-file only).

    This endpoint is retained for backward compatibility and emergency fallback.
    Primary path for local imports is upload session:
    - POST /import-jobs/{job_id}/upload-sessions
    - PUT /upload-sessions/{session_id}/parts/{part_number}
    - POST /upload-sessions/{session_id}/complete

    Validates:
    - Job exists and belongs to user
    - Job is local_file type
    - Job is in created status
    - File is valid PDF (magic bytes)
    - File size <= 50MB
    """
    try:
        service = ImportJobService()
        job = await service.get_job(job_id, user_id, db)

        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Import job not found"),
            )

        if job.source_type != "local_file":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Only local_file jobs accept uploads"),
            )

        if job.status != "created":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(f"Job not in created status (current: {job.status})"),
            )

        # Validate file
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Only PDF files are accepted"),
            )

        # Read content for validation
        content = await file.read()

        # Validate magic bytes
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Invalid PDF: magic bytes check failed"),
            )

        # Validate size
        max_size = 50 * 1024 * 1024  # 50MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("File exceeds 50MB limit"),
            )

        # Generate storage key
        storage_key = (
            f"uploads/{user_id}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{job_id}.pdf"
        )

        # Write to local storage
        local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        file_path = os.path.join(local_storage_path, storage_key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate SHA256
        sha256 = hashlib.sha256(content).hexdigest()

        # Update job with file info
        await service.set_file_info(
            job=job,
            storage_key=storage_key,
            sha256=sha256,
            size_bytes=len(content),
            filename=file.filename,
            mime_type="application/pdf",
            db=db,
        )

        logger.info(
            "File uploaded to ImportJob",
            job_id=job_id,
            storage_key=storage_key,
            sha256=sha256,
            size_bytes=len(content),
        )

        # Trigger worker processing (Wave 5)
        from app.workers.import_worker import process_import_job
        process_import_job.delay(job_id)

        return KBResponse(
            success=True,
            data={
                "importJobId": job_id,
                "status": "queued",
                "stage": "uploaded",
                "progress": 10,
                "pathMode": "fallback_small_file_only",
                "file": {
                    "storageKey": storage_key,
                    "sha256": sha256,
                    "sizeBytes": len(content),
                },
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload file to ImportJob", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to upload file: {str(e)}"),
        )


# =============================================================================
# Get ImportJob Endpoint
# =============================================================================


@router.get("/import-jobs/{job_id}", response_model=KBResponse)
async def get_import_job(
    job_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get ImportJob status with next_action."""
    try:
        service = ImportJobService()
        job = await service.get_job(job_id, user_id, db)

        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Import job not found"),
            )

        return KBResponse(
            success=True,
            data={
                "importJobId": job.id,
                "knowledgeBaseId": job.knowledge_base_id,
                "sourceType": job.source_type,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "nextAction": job.next_action,
                "source": {
                    "rawInput": job.source_ref_raw,
                    "normalizedRef": job.source_ref_normalized,
                    "externalIds": job.external_ids or {},
                },
                "preview": {
                    "title": job.resolved_title,
                    "authors": job.resolved_authors or [],
                    "year": job.resolved_year,
                    "venue": job.resolved_venue,
                },
                "file": {
                    "storageKey": job.storage_key,
                    "sha256": job.file_sha256,
                    "sizeBytes": job.size_bytes,
                }
                if job.storage_key
                else None,
                "dedupe": {
                    "status": job.dedupe_status,
                    "matchedPaperId": job.dedupe_match_paper_id,
                    "decision": job.dedupe_decision,
                },
                "paper": {"paperId": job.paper_id} if job.paper_id else None,
                "task": {"processingTaskId": job.processing_task_id}
                if job.processing_task_id
                else None,
                "error": {
                    "code": job.error_code,
                    "message": job.error_message,
                }
                if job.error_code
                else None,
                "createdAt": job.created_at.isoformat() if job.created_at else None,
                "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get ImportJob", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get import job: {str(e)}"),
        )


# =============================================================================
# List ImportJobs Endpoint
# =============================================================================


@router.get("/import-jobs", response_model=KBResponse)
async def list_import_jobs(
    knowledgeBaseId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """List ImportJobs for user with optional filters."""
    try:
        service = ImportJobService()
        jobs = await service.list_jobs(
            user_id=user_id,
            kb_id=knowledgeBaseId,
            status=status,
            limit=limit,
            offset=offset,
            db=db,
        )

        return KBResponse(
            success=True,
            data={
                "jobs": [
                    {
                        "importJobId": j.id,
                        "knowledgeBaseId": j.knowledge_base_id,
                        "sourceType": j.source_type,
                        "status": j.status,
                        "stage": j.stage,
                        "progress": j.progress,
                        "nextAction": j.next_action,
                        "source": {
                            "rawInput": j.source_ref_raw,
                        },
                        "preview": {
                            "title": j.resolved_title,
                            "year": j.resolved_year,
                        },
                        "paper": {"paperId": j.paper_id} if j.paper_id else None,
                        "error": {"message": getattr(j, 'error_message', None)} if getattr(j, 'error_message', None) else None,
                        "createdAt": j.created_at.isoformat() if j.created_at else None,
                    }
                    for j in jobs
                ],
                "total": len(jobs),
                "limit": limit,
                "offset": offset,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list ImportJobs", error=str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list import jobs: {str(e)}"),
        )


# =============================================================================
# Wave 5: Retry and Cancel Endpoints
# =============================================================================


class RetryRequest(BaseModel):
    """Request to retry a failed ImportJob."""

    retryFromStage: Optional[str] = Field(
        default=None,
        description="Stage to retry from (resolve_source, download_pdf, etc.)",
    )


@router.post("/import-jobs/{job_id}/retry", response_model=KBResponse)
async def retry_import_job(
    job_id: str,
    request: Optional[RetryRequest] = None,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed import job.

    Per gpt意见.md 2.4.4: Only allow retry for failed status.
    Resets status to queued and triggers worker.

    Args:
        job_id: ImportJob ID to retry
        request: Optional retry stage specification
        user_id: User ID for ownership check
        db: Database session

    Returns:
        Updated ImportJob status
    """
    try:
        service = ImportJobService()
        job = await service.get_job(job_id, user_id, db)

        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Import job not found"),
            )

        if job.status != "failed":
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Only failed jobs can be retried"),
            )

        # Reset status
        job.status = "queued"
        job.stage = (
            request.retryFromStage if request and request.retryFromStage
            else "resolving_source"
        )
        job.error_code = None
        job.error_message = None
        job.retry_count += 1
        job.updated_at = datetime.now(timezone.utc)
        job.next_action = None  # Worker handles next steps
        await db.commit()

        logger.info(
            "ImportJob retry triggered",
            job_id=job_id,
            retry_count=job.retry_count,
            retry_from_stage=job.stage,
        )

        # Re-trigger worker
        from app.workers.import_worker import process_import_job
        process_import_job.delay(job_id)

        return KBResponse(
            success=True,
            data={
                "importJobId": job_id,
                "status": "queued",
                "stage": job.stage,
                "retryCount": job.retry_count,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry ImportJob", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to retry import job: {str(e)}"),
        )


@router.post("/import-jobs/{job_id}/cancel", response_model=KBResponse)
async def cancel_import_job(
    job_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or queued import job.

    Per gpt意见.md 2.4.5: Cancel jobs not yet completed.
    Sets status to cancelled and clears next_action.

    Args:
        job_id: ImportJob ID to cancel
        user_id: User ID for ownership check
        db: Database session

    Returns:
        Cancelled ImportJob status
    """
    try:
        service = ImportJobService()
        job = await service.get_job(job_id, user_id, db)

        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Import job not found"),
            )

        if job.status in ["completed", "cancelled"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Cannot cancel completed or already cancelled job"),
            )

        # Use service method for consistent state update
        await service.set_cancelled(job, db)

        # Log event
        await service.add_event(
            job,
            level="info",
            event_type="job_cancelled",
            message="User cancelled import",
            db=db,
        )

        logger.info(
            "ImportJob cancelled by user",
            job_id=job_id,
            previous_status=job.status,
        )

        return KBResponse(
            success=True,
            data={
                "importJobId": job_id,
                "status": "cancelled",
                "cancelledAt": job.cancelled_at.isoformat() if job.cancelled_at else None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel ImportJob", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to cancel import job: {str(e)}"),
        )


__all__ = ["router"]