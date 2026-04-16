"""Upload management API routes.

Migrated from Node.js uploads.ts, batch.ts, upload-history.ts.
Migrated to SQLAlchemy ORM from legacy postgres_db.

Endpoints:
- POST /api/v1/uploads - Single file upload
- POST /api/v1/uploads/batch - Create batch upload session
- POST /api/v1/uploads/batch/:id/files - Upload file to batch
- GET /api/v1/uploads/batch/:id/progress - Get batch progress
- GET /api/v1/uploads/history - Get upload history
- POST /api/v1/uploads/history - Record external URL upload
- DELETE /api/v1/uploads/history/:id - Delete upload history entry
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Paper, UploadHistory, ProcessingTask, PaperBatch
from app.middleware.auth import get_current_user
from app.services.auth_service import User
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger
from app.config import settings


router = APIRouter(tags=["Uploads"])


# =============================================================================
# Constants
# =============================================================================

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_FILES = 50


# =============================================================================
# Request/Response Models
# =============================================================================

class UploadResponse(BaseModel):
    """Upload response."""
    success: bool = True
    data: dict


class BatchCreateRequest(BaseModel):
    """Request to create a batch upload session."""
    files: List[dict] = Field(..., description="List of files with filename, fileSize, optional title/doi")


class BatchFileUpload(BaseModel):
    """Request to upload a file to a batch."""
    filename: str
    fileSize: int
    title: Optional[str] = None
    doi: Optional[str] = None


class ExternalUrlUpload(BaseModel):
    """Request to record an external URL upload."""
    url: str
    title: str
    source: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def _create_error_response(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    instance: str,
) -> HTTPException:
    """Create HTTPException with RFC 7807 ProblemDetail."""
    problem = ProblemDetail(
        type=error_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
    )
    return HTTPException(
        status_code=status_code,
        detail=problem.to_dict(),
    )


def _get_progress_percent(processing_status: str) -> int:
    """Calculate progress percentage based on processing status."""
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
    return progress_map.get(processing_status, 0)


def _get_processing_stage(status: str) -> str:
    """Get human-readable processing stage name."""
    stage_names = {
        "processing_ocr": "OCR Processing",
        "parsing": "Parsing Document",
        "extracting_imrad": "Extracting Structure",
        "generating_notes": "Generating Notes",
        "storing_vectors": "Storing Vectors",
        "indexing_multimodal": "Indexing Multimodal",
        "completed": "Completed",
        "failed": "Failed",
        "pending": "Pending",
    }
    return stage_names.get(status, status)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_single_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single PDF file.

    Form data:
        file: PDF file (max 50MB)

    Returns:
        Paper ID and processing status.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)
    request_id = str(uuid.uuid4())

    # Validate file
    if not file:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="No file uploaded. Use form field name 'file'",
            instance=instance,
        )

    filename = file.filename or "untitled.pdf"

    # Check file extension
    if not filename.lower().endswith(".pdf"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="Only PDF files are accepted",
            instance=instance,
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise _create_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_type=ErrorTypes.FILE_TOO_LARGE,
            title="File Too Large",
            detail=f"File size ({file_size} bytes) exceeds maximum ({MAX_FILE_SIZE} bytes)",
            instance=instance,
        )

    # Validate PDF magic bytes
    if not content.startswith(b"%PDF-"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="File is not a valid PDF (magic bytes check failed)",
            instance=instance,
        )

    # Extract title from filename
    title = filename.replace(".pdf", "").replace(".PDF", "")

    # Check for duplicates
    existing_result = await db.execute(
        select(Paper.id).where(
            Paper.user_id == user_id,
            Paper.title == title,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise _create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists',
            instance=instance,
        )

    # Generate storage key
    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"
    local_storage_path = settings.LOCAL_STORAGE_PATH
    file_path = os.path.join(local_storage_path, storage_key)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create paper record
    paper_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    paper = Paper(
        id=paper_id,
        title=title,
        authors=[],
        status="processing",
        user_id=user_id,
        storage_key=storage_key,
        file_size=file_size,
        keywords=[],
        upload_status="processing",
        upload_progress=0,
        uploaded_at=now,
    )
    db.add(paper)

    # Create upload history record
    upload_history_id = str(uuid.uuid4())
    upload_history = UploadHistory(
        id=upload_history_id,
        user_id=user_id,
        paper_id=paper_id,
        filename=filename,
        status="PROCESSING",
    )
    db.add(upload_history)

    # Create processing task
    task_id = str(uuid.uuid4())
    processing_task = ProcessingTask(
        id=task_id,
        paper_id=paper_id,
        status="pending",
        storage_key=storage_key,
    )
    db.add(processing_task)

    await db.commit()

    logger.info(
        "Single file upload completed",
        user_id=user_id,
        paper_id=paper_id,
        filename=filename,
        file_size=file_size,
        request_id=request_id,
    )

    return UploadResponse(
        success=True,
        data={
            "paperId": paper_id,
            "taskId": task_id,
            "status": "pending",
            "message": "File uploaded successfully. Processing started.",
        },
    )


@router.post("/batch", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    request: Request,
    body: BatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a batch upload session.

    Request body:
        files: Array of file info objects

    Returns:
        Batch ID and presigned URLs for each file.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)
    request_id = str(uuid.uuid4())

    files = body.files

    # Validate files array
    if not files or not isinstance(files, list) or len(files) == 0:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="files array is required and must not be empty",
            instance=instance,
        )

    # Max 50 files per batch
    if len(files) > MAX_BATCH_FILES:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail=f"Maximum {MAX_BATCH_FILES} files allowed per batch",
            instance=instance,
        )

    # Validate each file
    for i, file_info in enumerate(files):
        if not file_info.get("filename"):
            raise _create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorTypes.VALIDATION_ERROR,
                title="Validation Error",
                detail=f"File at index {i} missing filename",
                instance=instance,
            )

        if not file_info.get("fileSize"):
            raise _create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorTypes.VALIDATION_ERROR,
                title="Validation Error",
                detail=f"File at index {i} missing fileSize",
                instance=instance,
            )

        filename = file_info["filename"]
        if not filename.lower().endswith(".pdf"):
            raise _create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorTypes.VALIDATION_ERROR,
                title="Validation Error",
                detail=f"File '{filename}' is not a PDF",
                instance=instance,
            )

    # Create batch record
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    batch = PaperBatch(
        id=batch_id,
        user_id=user_id,
        total_files=len(files),
        uploaded_count=0,
        status="uploading",
    )
    db.add(batch)

    # Create paper records and generate upload URLs
    papers = []
    for file_info in files:
        paper_id = str(uuid.uuid4())
        filename = file_info["filename"]
        title = file_info.get("title") or filename.replace(".pdf", "")
        storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"

        # Create paper record
        paper = Paper(
            id=paper_id,
            user_id=user_id,
            batch_id=batch_id,
            title=title,
            authors=[],
            storage_key=storage_key,
            file_size=file_info.get("fileSize"),
            doi=file_info.get("doi"),
            status="pending",
            upload_status="pending",
            upload_progress=0,
            keywords=[],
        )
        db.add(paper)

        # Generate upload URL (local storage)
        upload_url = f"/api/v1/uploads/local/{storage_key}"

        papers.append({
            "id": paper_id,
            "uploadUrl": upload_url,
            "filename": filename,
        })

    await db.commit()

    logger.info(
        "Batch upload created",
        user_id=user_id,
        batch_id=batch_id,
        total_files=len(files),
        request_id=request_id,
    )

    return UploadResponse(
        success=True,
        data={
            "batchId": batch_id,
            "totalFiles": len(files),
            "papers": papers,
        },
    )


@router.get("/batch/{batch_id}", response_model=UploadResponse)
async def get_batch(
    request: Request,
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get batch status.

    Path parameters:
        batch_id: Batch ID

    Returns:
        Batch information.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    batch_result = await db.execute(
        select(PaperBatch).where(
            PaperBatch.id == batch_id,
            PaperBatch.user_id == user_id,
        )
    )
    batch = batch_result.scalar_one_or_none()

    if not batch:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Batch not found",
            instance=instance,
        )

    return UploadResponse(
        success=True,
        data={
            "id": batch.id,
            "user_id": batch.user_id,
            "total_files": batch.total_files,
            "uploaded_count": batch.uploaded_count,
            "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
        },
    )


@router.get("/batch/{batch_id}/progress", response_model=UploadResponse)
async def get_batch_progress(
    request: Request,
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed batch progress.

    Path parameters:
        batch_id: Batch ID

    Returns:
        Detailed progress information for all files in batch.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    # Query batch
    batch_result = await db.execute(
        select(PaperBatch).where(
            PaperBatch.id == batch_id,
            PaperBatch.user_id == user_id,
        )
    )
    batch = batch_result.scalar_one_or_none()

    if not batch:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Batch not found",
            instance=instance,
        )

    # Query papers with processing tasks using join
    papers_result = await db.execute(
        select(
            Paper.id,
            Paper.title,
            Paper.upload_status,
            Paper.upload_progress,
            Paper.uploaded_at,
            ProcessingTask.status.label("processing_status"),
            ProcessingTask.error_message,
            ProcessingTask.updated_at.label("last_updated"),
        )
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.batch_id == batch_id)
        .order_by(Paper.created_at)
    )
    papers = papers_result.all()

    # Calculate statistics
    uploaded_count = sum(1 for p in papers if p.upload_status == "completed")
    processing_count = sum(1 for p in papers if p.processing_status not in ("completed", "failed", "pending", None))
    completed_count = sum(1 for p in papers if p.processing_status == "completed")
    failed_count = sum(1 for p in papers if p.processing_status == "failed")

    total_files = batch.total_files

    # Calculate overall progress: upload (20%) + processing (80%)
    upload_progress = int((uploaded_count / total_files) * 20) if total_files > 0 else 0
    processing_progress = int((completed_count / total_files) * 80) if total_files > 0 else 0
    overall_progress = upload_progress + processing_progress

    # Format per-file progress
    formatted_papers = []
    for paper in papers:
        processing_status = paper.processing_status or "pending"
        formatted_papers.append({
            "id": paper.id,
            "filename": paper.title or "Untitled",
            "uploadStatus": paper.upload_status or "pending",
            "uploadProgress": paper.upload_progress or 0,
            "processingStatus": processing_status,
            "processingProgress": _get_progress_percent(processing_status),
            "processingStage": _get_processing_stage(processing_status),
            "errorMessage": paper.error_message,
            "uploadedAt": paper.uploaded_at.isoformat() if paper.uploaded_at else None,
        })

    return UploadResponse(
        success=True,
        data={
            "batchId": batch_id,
            "totalFiles": total_files,
            "status": batch.status,
            "uploadedCount": uploaded_count,
            "uploadProgress": int((uploaded_count / total_files) * 100) if total_files > 0 else 0,
            "processingCount": processing_count,
            "completedCount": completed_count,
            "failedCount": failed_count,
            "overallProgress": overall_progress,
            "papers": formatted_papers,
        },
    )


@router.post("/batch/{batch_id}/files", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_batch_file(
    request: Request,
    batch_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to a batch.

    Path parameters:
        batch_id: Batch ID

    Form data:
        file: PDF file

    Returns:
        Paper ID for the uploaded file.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    # Verify batch exists
    batch_result = await db.execute(
        select(PaperBatch).where(
            PaperBatch.id == batch_id,
            PaperBatch.user_id == user_id,
        )
    )
    batch = batch_result.scalar_one_or_none()

    if not batch:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Batch not found",
            instance=instance,
        )

    # Validate file
    if not file:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="No file uploaded",
            instance=instance,
        )

    filename = file.filename or "untitled.pdf"

    if not filename.lower().endswith(".pdf"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="Only PDF files are accepted",
            instance=instance,
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise _create_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_type=ErrorTypes.FILE_TOO_LARGE,
            title="File Too Large",
            detail="File exceeds 50MB limit",
            instance=instance,
        )

    if not content.startswith(b"%PDF-"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="File is not a valid PDF",
            instance=instance,
        )

    # Generate storage key and save
    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Find a pending paper in this batch or create one
    pending_paper_result = await db.execute(
        select(Paper).where(
            Paper.batch_id == batch_id,
            Paper.user_id == user_id,
            Paper.upload_status == "pending",
        ).limit(1)
    )
    pending_paper = pending_paper_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if pending_paper:
        # Update existing paper
        paper_id = pending_paper.id
        pending_paper.title = filename.replace(".pdf", "")
        pending_paper.storage_key = storage_key
        pending_paper.file_size = file_size
        pending_paper.upload_status = "completed"
        pending_paper.upload_progress = 100
        pending_paper.uploaded_at = now
    else:
        # Create new paper
        paper_id = str(uuid.uuid4())

        paper = Paper(
            id=paper_id,
            user_id=user_id,
            batch_id=batch_id,
            title=filename.replace(".pdf", ""),
            authors=[],
            storage_key=storage_key,
            file_size=file_size,
            status="pending",
            upload_status="completed",
            upload_progress=100,
            keywords=[],
            uploaded_at=now,
        )
        db.add(paper)

    # Increment batch uploaded count
    new_count = batch.uploaded_count + 1
    batch.uploaded_count = new_count
    batch.updated_at = now

    # If all files uploaded, update status and trigger processing
    if new_count >= batch.total_files:
        batch.status = "processing"

        # Create processing tasks for all pending papers
        pending_papers_result = await db.execute(
            select(Paper.id, Paper.storage_key).where(
                Paper.batch_id == batch_id,
                Paper.status == "pending",
            )
        )
        pending_papers = pending_papers_result.all()

        for paper_row in pending_papers:
            task_id = str(uuid.uuid4())
            processing_task = ProcessingTask(
                id=task_id,
                paper_id=paper_row.id,
                status="pending",
                storage_key=paper_row.storage_key,
            )
            db.add(processing_task)

            # Update paper status to processing
            await db.execute(
                update(Paper).where(Paper.id == paper_row.id).values(status="processing")
            )

    await db.commit()

    logger.info(
        "Batch file uploaded",
        user_id=user_id,
        batch_id=batch_id,
        paper_id=paper_id,
        filename=filename,
    )

    return UploadResponse(
        success=True,
        data={
            "paperId": paper_id,
            "uploadedCount": new_count,
            "totalFiles": batch.total_files,
        },
    )


@router.get("/history", response_model=UploadResponse)
async def get_upload_history(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upload history for user.

    Query parameters:
        limit: Items per page (default 50, max 100)
        offset: Offset for pagination

    Returns:
        List of upload history records.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    # Validate pagination
    limit = min(100, max(1, limit))
    offset = max(0, offset)

    # Query upload history with paper details using join
    records_result = await db.execute(
        select(
            UploadHistory,
            Paper.title.label("paper_title"),
            ProcessingTask.status.label("processing_status"),
            ProcessingTask.error_message.label("task_error"),
            ProcessingTask.updated_at.label("task_updated_at"),
            ProcessingTask.completed_at.label("task_completed_at"),
        )
        .outerjoin(Paper, UploadHistory.paper_id == Paper.id)
        .outerjoin(ProcessingTask, UploadHistory.paper_id == ProcessingTask.paper_id)
        .where(UploadHistory.user_id == user_id)
        .order_by(UploadHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = records_result.all()

    # Get total count
    total_result = await db.execute(
        select(func.count(UploadHistory.id)).where(UploadHistory.user_id == user_id)
    )
    total = total_result.scalar() or 0

    # Format records
    formatted_records = []
    for row in records:
        upload_hist = row[0]  # UploadHistory object
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
            progress = _get_progress_percent(processing_status)

        formatted_records.append({
            "id": upload_hist.id,
            "user_id": upload_hist.user_id,
            "paper_id": upload_hist.paper_id,
            "filename": upload_hist.filename,
            "status": display_status,
            "chunks_count": upload_hist.chunks_count,
            "llm_tokens": upload_hist.llm_tokens,
            "page_count": upload_hist.page_count,
            "image_count": upload_hist.image_count,
            "table_count": upload_hist.table_count,
            "error_message": upload_hist.error_message or row.task_error,
            "processing_time": upload_hist.processing_time,
            "created_at": upload_hist.created_at.isoformat() if upload_hist.created_at else None,
            "updated_at": (
                row.task_updated_at.isoformat()
                if row.task_updated_at
                else (
                    upload_hist.updated_at.isoformat() if upload_hist.updated_at else None
                )
            ),
            "completedAt": row.task_completed_at.isoformat() if row.task_completed_at else None,
            "processingStatus": processing_status,
            "progress": progress,
            "paper_title": row.paper_title,
            "paper_status": row.processing_status,
        })

    return UploadResponse(
        success=True,
        data={
            "records": formatted_records,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/history/{upload_id}", response_model=UploadResponse)
async def get_upload_history_record(
    request: Request,
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single upload history record."""
    instance = str(request.url.path)
    user_id = str(current_user.id)

    record_result = await db.execute(
        select(
            UploadHistory,
            Paper.title.label("paper_title"),
            ProcessingTask.status.label("processing_status"),
            ProcessingTask.error_message.label("task_error"),
            ProcessingTask.updated_at.label("task_updated_at"),
            ProcessingTask.completed_at.label("task_completed_at"),
        )
        .outerjoin(Paper, UploadHistory.paper_id == Paper.id)
        .outerjoin(ProcessingTask, UploadHistory.paper_id == ProcessingTask.paper_id)
        .where(
            UploadHistory.id == upload_id,
            UploadHistory.user_id == user_id,
        )
    )
    row = record_result.first()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Upload history record not found",
            instance=instance,
        )

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
        progress = _get_progress_percent(processing_status)

    return UploadResponse(
        success=True,
        data={
            "id": upload_hist.id,
            "user_id": upload_hist.user_id,
            "paper_id": upload_hist.paper_id,
            "filename": upload_hist.filename,
            "status": display_status,
            "chunks_count": upload_hist.chunks_count,
            "llm_tokens": upload_hist.llm_tokens,
            "page_count": upload_hist.page_count,
            "image_count": upload_hist.image_count,
            "table_count": upload_hist.table_count,
            "error_message": upload_hist.error_message or row.task_error,
            "processing_time": upload_hist.processing_time,
            "created_at": upload_hist.created_at.isoformat() if upload_hist.created_at else None,
            "updated_at": (
                row.task_updated_at.isoformat()
                if row.task_updated_at
                else (
                    upload_hist.updated_at.isoformat() if upload_hist.updated_at else None
                )
            ),
            "completedAt": row.task_completed_at.isoformat() if row.task_completed_at else None,
            "processingStatus": processing_status,
            "progress": progress,
            "paper_title": row.paper_title,
            "paper_status": row.processing_status,
        },
    )


@router.post("/history", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def record_external_upload(
    request: Request,
    body: ExternalUrlUpload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an external URL upload.

    Request body:
        url: External URL
        title: Paper title
        source: Source identifier

    Returns:
        Upload history ID.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    # Create upload history record
    upload_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    upload_history = UploadHistory(
        id=upload_id,
        user_id=user_id,
        filename=body.title,
        status="EXTERNAL",
    )
    db.add(upload_history)
    await db.commit()

    logger.info(
        "External upload recorded",
        user_id=user_id,
        upload_id=upload_id,
        url=body.url,
        source=body.source,
    )

    return UploadResponse(
        success=True,
        data={
            "uploadId": upload_id,
            "message": "External upload recorded",
        },
    )


@router.delete("/history/{upload_id}")
async def delete_upload_history(
    request: Request,
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an upload history record.

    Path parameters:
        upload_id: Upload history ID

    Returns:
        Success message.
    """
    instance = str(request.url.path)
    user_id = str(current_user.id)

    # Verify record exists and belongs to user
    record_result = await db.execute(
        select(UploadHistory.id, UploadHistory.paper_id).where(
            UploadHistory.id == upload_id,
            UploadHistory.user_id == user_id,
        )
    )
    record = record_result.first()

    if not record:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Upload history record not found",
            instance=instance,
        )

    paper_id = record.paper_id

    # Delete record (paper is preserved)
    await db.execute(
        delete(UploadHistory).where(UploadHistory.id == upload_id)
    )
    await db.commit()

    logger.info(
        "Upload history deleted",
        user_id=user_id,
        upload_id=upload_id,
        paper_preserved=paper_id is not None,
    )

    return UploadResponse(
        success=True,
        data={
            "message": "Upload history record deleted successfully",
            "paperPreserved": paper_id is not None,
        },
    )


__all__ = ["router"]
