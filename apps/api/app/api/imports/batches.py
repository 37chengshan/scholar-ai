"""Batch Import API endpoints.

Per gpt意见.md Section 2.1.2: POST /knowledge-bases/{kb_id}/imports/batch
Per gpt意见.md Section 2.4.3: GET /import-batches/{batch_id}

Endpoints:
- POST /knowledge-bases/{kb_id}/imports/batch - Create batch import
- GET /import-batches/{batch_id} - Get batch status with aggregate counts
- POST /import-batches/{batch_id}/files - Upload local files for batch jobs
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from pydantic import BaseModel, Field, ValidationError
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


class BatchFileManifestItem(BaseModel):
    """Manifest entry used to map uploaded file to import job."""

    importJobId: str
    filename: str


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
                auto_commit=False,
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
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.validation(str(e)),
        )
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create batch import", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create batch import: {str(e)}"),
        )


@router.post("/import-batches/{batch_id}/files", response_model=KBResponse)
async def upload_batch_local_files(
    batch_id: str,
    manifest: str = Form(...),
    files: List[UploadFile] = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple local PDFs for pre-created local_file jobs in a batch.

    Request shape:
    - manifest: JSON array [{"importJobId":"...","filename":"..."}, ...]
    - files: multipart files, matched by filename in manifest
    """
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("No files uploaded"),
            )

        try:
            raw_manifest = json.loads(manifest)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(f"Invalid manifest JSON: {str(e)}"),
            )

        if not isinstance(raw_manifest, list) or not raw_manifest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("manifest must be a non-empty array"),
            )

        try:
            manifest_items = [BatchFileManifestItem.model_validate(i) for i in raw_manifest]
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(f"Invalid manifest item: {str(e)}"),
            )

        manifest_job_ids = [item.importJobId for item in manifest_items]
        if len(set(manifest_job_ids)) != len(manifest_job_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("manifest contains duplicate importJobId entries"),
            )

        manifest_filenames = [item.filename for item in manifest_items]
        if len(set(manifest_filenames)) != len(manifest_filenames):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("manifest contains duplicate filename entries"),
            )

        if len(files) > len(manifest_items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(
                    f"Too many files for manifest: manifest={len(manifest_items)}, files={len(files)}"
                ),
            )

        batch_result = await db.execute(
            select(ImportBatch).where(
                ImportBatch.id == batch_id,
                ImportBatch.user_id == user_id,
            )
        )
        batch = batch_result.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Batch not found"),
            )

        seen_file_names = set()
        upload_by_name: Dict[str, UploadFile] = {}
        for upload in files:
            if not upload.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Errors.validation("All files must have filename"),
                )
            if upload.filename in seen_file_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Errors.validation(f"Duplicate filename in files: {upload.filename}"),
                )
            seen_file_names.add(upload.filename)
            upload_by_name[upload.filename] = upload

        extra_uploads = set(upload_by_name.keys()) - set(manifest_filenames)
        if extra_uploads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(
                    f"Files not referenced by manifest: {sorted(extra_uploads)}"
                ),
            )

        job_ids = [item.importJobId for item in manifest_items]
        jobs_result = await db.execute(
            select(ImportJob).where(
                ImportJob.id.in_(job_ids),
                ImportJob.batch_id == batch_id,
                ImportJob.user_id == user_id,
            )
        )
        jobs = jobs_result.scalars().all()
        jobs_by_id = {job.id: job for job in jobs}

        service = ImportJobService()
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        max_size = 50 * 1024 * 1024

        for item in manifest_items:
            upload = upload_by_name.get(item.filename)
            job = jobs_by_id.get(item.importJobId)

            if not job:
                rejected.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "reason": "Import job not found in this batch",
                    }
                )
                continue

            if job.source_type != "local_file":
                rejected.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "reason": f"Job source_type must be local_file (got {job.source_type})",
                    }
                )
                continue

            if job.status != "created":
                rejected.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "reason": f"Job not in created status (current: {job.status})",
                    }
                )
                continue

            if not upload:
                rejected.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "reason": "No uploaded file matches manifest filename",
                    }
                )
                continue

            try:
                content = await upload.read()

                if not item.filename.lower().endswith(".pdf"):
                    rejected.append(
                        {
                            "importJobId": item.importJobId,
                            "filename": item.filename,
                            "reason": "Only PDF files are accepted",
                        }
                    )
                    continue

                if not content.startswith(b"%PDF-"):
                    rejected.append(
                        {
                            "importJobId": item.importJobId,
                            "filename": item.filename,
                            "reason": "Invalid PDF: magic bytes check failed",
                        }
                    )
                    continue

                if len(content) > max_size:
                    rejected.append(
                        {
                            "importJobId": item.importJobId,
                            "filename": item.filename,
                            "reason": "File exceeds 50MB limit",
                        }
                    )
                    continue

                storage_key = (
                    f"uploads/{user_id}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{item.importJobId}.pdf"
                )
                local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
                file_path = os.path.join(local_storage_path, storage_key)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(content)

                sha256 = hashlib.sha256(content).hexdigest()
                await service.set_file_info(
                    job=job,
                    storage_key=storage_key,
                    sha256=sha256,
                    size_bytes=len(content),
                    filename=item.filename,
                    mime_type="application/pdf",
                    db=db,
                )

                from app.workers.import_worker import process_import_job

                try:
                    process_import_job.delay(item.importJobId)
                except Exception as queue_error:
                    await service.set_error(
                        job=job,
                        error_code="QUEUE_SUBMIT_FAILED",
                        error_message="Failed to enqueue import job",
                        db=db,
                        error_detail={"reason": str(queue_error)},
                    )
                    rejected.append(
                        {
                            "importJobId": item.importJobId,
                            "filename": item.filename,
                            "reason": f"Failed to enqueue import job: {str(queue_error)}",
                        }
                    )
                    continue

                accepted.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "status": "queued",
                    }
                )
            except Exception as item_error:
                rejected.append(
                    {
                        "importJobId": item.importJobId,
                        "filename": item.filename,
                        "reason": str(item_error),
                    }
                )

        logger.info(
            "Batch local files uploaded",
            batch_id=batch_id,
            accepted=len(accepted),
            rejected=len(rejected),
        )

        return KBResponse(
            success=True,
            data={
                "batchJobId": batch_id,
                "totalItems": len(manifest_items),
                "acceptedCount": len(accepted),
                "rejectedCount": len(rejected),
                "accepted": accepted,
                "rejected": rejected,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload batch local files", error=str(e), batch_id=batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to upload batch files: {str(e)}"),
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