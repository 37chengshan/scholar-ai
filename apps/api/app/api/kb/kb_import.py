"""KB Import operations - Upload PDF, import from URL/arXiv, upload history.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.
Per D-01: kb_import.py contains upload/import/upload-history endpoints.

Endpoints:
- POST /api/v1/knowledge-bases/{kb_id}/upload - Upload PDF to KB
- POST /api/v1/knowledge-bases/{kb_id}/import-url - Import from URL/DOI
- POST /api/v1/knowledge-bases/{kb_id}/import-arxiv - Import from arXiv
- POST /api/v1/knowledge-bases/{kb_id}/batch-upload - Batch upload
- GET /api/v1/knowledge-bases/{kb_id}/upload-history - Upload history
- DELETE /api/v1/knowledge-bases/{kb_id}/upload-history/{id} - Delete upload history
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
from app.models.task import ProcessingTask
from app.models.upload_history import UploadHistory
from app.deps import CurrentUserId
from app.services.import_job_service import ImportJobService
from app.utils.problem_detail import Errors
from app.utils.logger import logger
from app.workers.import_worker import process_import_job


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBImportUrl(BaseModel):
    """Request to import paper from URL/DOI."""

    url: str


class KBImportArxiv(BaseModel):
    """Request to import paper from arXiv."""

    arxivId: str


async def _get_kb_or_404(kb_id: str, user_id: str, db: AsyncSession) -> KnowledgeBase:
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == user_id,
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Errors.not_found("Knowledge base not found"),
        )
    return kb


async def _read_and_validate_pdf(file: UploadFile) -> Tuple[bytes, str]:
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.validation("No file uploaded. Use form field name 'file'"),
        )

    filename = file.filename or "untitled.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.validation("Only PDF files are accepted"),
        )

    content = await file.read()
    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=Errors.validation("File size exceeds 50MB limit"),
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.validation("File is not a valid PDF"),
        )

    return content, filename


def _build_storage_key(user_id: str, import_job_id: str) -> str:
    now = datetime.now(timezone.utc)
    return f"uploads/{user_id}/{now.strftime('%Y/%m/%d')}/{import_job_id}.pdf"


async def _save_pdf(storage_key: str, content: bytes) -> None:
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    async with aiofiles.open(file_path, "wb") as output_file:
        await output_file.write(content)


async def _create_local_file_import_job(
    *,
    kb_id: str,
    user_id: str,
    filename: str,
    content: bytes,
    db: AsyncSession,
) -> Dict[str, Any]:
    service = ImportJobService()
    job = await service.create_job(
        user_id=user_id,
        kb_id=kb_id,
        source_type="local_file",
        source_ref_raw=filename,
        options={},
        db=db,
    )

    storage_key = _build_storage_key(user_id, job.id)
    await _save_pdf(storage_key, content)

    import hashlib

    await service.set_file_info(
        job=job,
        storage_key=storage_key,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        filename=filename,
        mime_type="application/pdf",
        db=db,
    )

    process_import_job.delay(job.id)

    return {
        "importJobId": job.id,
        "status": "queued",
        "stage": "uploaded",
        "progress": 10,
    }


# =============================================================================
# KB Import Endpoints
# =============================================================================


@router.post("/{kb_id}/upload", response_model=KBResponse)
async def upload_pdf_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF to a knowledge base.

    Legacy compatibility endpoint.
    Internally unified to ImportJob-first flow.
    """
    try:
        await _get_kb_or_404(kb_id, user_id, db)
        content, filename = await _read_and_validate_pdf(file)
        result = await _create_local_file_import_job(
            kb_id=kb_id,
            user_id=user_id,
            filename=filename,
            content=content,
            db=db,
        )

        logger.info(
            "Legacy KB upload routed to ImportJob pipeline",
            user_id=user_id,
            kb_id=kb_id,
            import_job_id=result["importJobId"],
            filename=filename,
            file_size=len(content),
        )

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "importJobId": result["importJobId"],
                "paperId": None,
                "taskId": result["importJobId"],
                "status": result["status"],
                "stage": result["stage"],
                "progress": result["progress"],
                "message": "File uploaded successfully. Import job queued.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to upload PDF to knowledge base", error=str(e), kb_id=kb_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to upload PDF: {str(e)}"),
        )


@router.post("/{kb_id}/import-url", response_model=KBResponse)
async def import_from_url(
    kb_id: str,
    request: KBImportUrl,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from URL/DOI via ImportJob pipeline."""
    try:
        await _get_kb_or_404(kb_id, user_id, db)
        if not request.url or not request.url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("url is required"),
            )

        service = ImportJobService()
        job = await service.create_job(
            user_id=user_id,
            kb_id=kb_id,
            source_type="pdf_url",
            source_ref_raw=request.url.strip(),
            options={},
            db=db,
        )
        process_import_job.delay(job.id)

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "importJobId": job.id,
                "paperId": None,
                "taskId": job.id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "message": "Import job queued.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import from URL", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to import from URL: {str(e)}"),
        )


@router.post("/{kb_id}/import-arxiv", response_model=KBResponse)
async def import_from_arxiv(
    kb_id: str,
    request: KBImportArxiv,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from arXiv via ImportJob pipeline."""
    try:
        await _get_kb_or_404(kb_id, user_id, db)
        if not request.arxivId or not request.arxivId.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("arxivId is required"),
            )

        service = ImportJobService()
        job = await service.create_job(
            user_id=user_id,
            kb_id=kb_id,
            source_type="arxiv",
            source_ref_raw=request.arxivId.strip(),
            options={},
            db=db,
        )
        process_import_job.delay(job.id)

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "importJobId": job.id,
                "paperId": None,
                "taskId": job.id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "message": "Import job queued.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import from arXiv", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to import from arXiv: {str(e)}"),
        )


@router.post("/{kb_id}/batch-upload", response_model=KBResponse)
async def batch_upload_to_kb(
    kb_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Batch upload PDFs to a knowledge base.

    Legacy compatibility endpoint.
    Internally routes each file to ImportJob-first pipeline.
    """
    try:
        await _get_kb_or_404(kb_id, user_id, db)

        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for file in files:
            try:
                content, filename = await _read_and_validate_pdf(file)
                result = await _create_local_file_import_job(
                    kb_id=kb_id,
                    user_id=user_id,
                    filename=filename,
                    content=content,
                    db=db,
                )
                accepted.append(
                    {
                        "importJobId": result["importJobId"],
                        "filename": filename,
                        "status": result["status"],
                    }
                )
            except HTTPException as e:
                rejected.append(
                    {
                        "filename": file.filename or "untitled.pdf",
                        "reason": str(e.detail),
                    }
                )
            except Exception as e:
                rejected.append(
                    {
                        "filename": file.filename or "untitled.pdf",
                        "reason": str(e),
                    }
                )

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "totalItems": len(files),
                "acceptedCount": len(accepted),
                "rejectedCount": len(rejected),
                "accepted": accepted,
                "rejected": rejected,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to batch upload to KB", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to batch upload to KB: {str(e)}"),
        )


@router.get("/{kb_id}/upload-history", response_model=KBResponse)
async def get_kb_upload_history(
    kb_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get upload history records related to papers in a specific KB."""
    try:
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

        records_result = await db.execute(
            select(
                UploadHistory,
                Paper.title.label("paper_title"),
                ProcessingTask.status.label("processing_status"),
                ProcessingTask.error_message.label("task_error"),
                ProcessingTask.updated_at.label("task_updated_at"),
                ProcessingTask.completed_at.label("task_completed_at"),
            )
            .join(Paper, UploadHistory.paper_id == Paper.id)
            .outerjoin(ProcessingTask, ProcessingTask.paper_id == Paper.id)
            .where(
                UploadHistory.user_id == user_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
            .order_by(UploadHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = records_result.all()

        total_result = await db.execute(
            select(func.count(UploadHistory.id))
            .select_from(UploadHistory)
            .join(Paper, UploadHistory.paper_id == Paper.id)
            .where(
                UploadHistory.user_id == user_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
        )
        total = total_result.scalar() or 0

        formatted_records = []
        for row in records:
            upload_hist = row[0]
            processing_status = row.processing_status or upload_hist.status.lower()
            display_status = upload_hist.status
            if row.processing_status:
                normalized = str(row.processing_status).lower()
                if normalized == "completed":
                    display_status = "COMPLETED"
                elif normalized == "failed":
                    display_status = "FAILED"
                else:
                    display_status = "PROCESSING"

            progress = 100 if display_status == "COMPLETED" else 0
            if display_status == "PROCESSING":
                progress_map = {
                    "pending": 0,
                    "processing_ocr": 15,
                    "parsing": 30,
                    "extracting_imrad": 45,
                    "generating_notes": 60,
                    "storing_vectors": 75,
                    "indexing_multimodal": 90,
                    "completed": 100,
                    "failed": 0,
                }
                progress = progress_map.get(processing_status, 0)

            formatted_records.append(
                {
                    "id": upload_hist.id,
                    "userId": upload_hist.user_id,
                    "paperId": upload_hist.paper_id,
                    "filename": upload_hist.filename,
                    "status": display_status,
                    "chunksCount": upload_hist.chunks_count,
                    "llmTokens": upload_hist.llm_tokens,
                    "pageCount": upload_hist.page_count,
                    "imageCount": upload_hist.image_count,
                    "tableCount": upload_hist.table_count,
                    "errorMessage": upload_hist.error_message or row.task_error,
                    "processingTime": upload_hist.processing_time,
                    "createdAt": upload_hist.created_at.isoformat()
                    if upload_hist.created_at
                    else None,
                    "updatedAt": (
                        row.task_updated_at.isoformat()
                        if row.task_updated_at
                        else (
                            upload_hist.updated_at.isoformat()
                            if upload_hist.updated_at
                            else None
                        )
                    ),
                    "completedAt": row.task_completed_at.isoformat()
                    if row.task_completed_at
                    else None,
                    "processingStatus": processing_status,
                    "progress": progress,
                    "paper": (
                        {
                            "id": upload_hist.paper_id,
                            "title": row.paper_title or upload_hist.filename,
                            "filename": upload_hist.filename,
                        }
                        if upload_hist.paper_id
                        else None
                    ),
                }
            )

        return KBResponse(
            success=True,
            data={
                "records": formatted_records,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get KB upload history", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get KB upload history: {str(e)}"),
        )


@router.delete("/{kb_id}/upload-history/{history_id}", response_model=KBResponse)
async def delete_kb_upload_history(
    kb_id: str,
    history_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Delete an upload history record."""
    try:
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

        history_result = await db.execute(
            select(UploadHistory).where(
                UploadHistory.id == history_id,
                UploadHistory.user_id == user_id,
            )
        )
        history = history_result.scalar_one_or_none()

        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Upload history record not found"),
            )

        await db.delete(history)
        logger.info("KB upload history deleted", history_id=history_id, kb_id=kb_id)

        return KBResponse(
            success=True,
            data={"id": history_id, "deleted": True},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete KB upload history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete upload history: {str(e)}"),
        )


__all__ = ["router"]
