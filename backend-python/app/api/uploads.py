"""Upload management API routes.

Migrated from Node.js uploads.ts, batch.ts, upload-history.ts.

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

from app.deps import get_current_user, postgres_db
from app.services.auth_service import User
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])


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
):
    """Upload a single PDF file.

    Form data:
        file: PDF file (max 50MB)

    Returns:
        Paper ID and processing status.
    """
    instance = str(request.url.path)
    user_id = current_user.id
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
    existing = await postgres_db.fetchrow(
        "SELECT id FROM papers WHERE user_id = $1 AND title = $2",
        user_id,
        title,
    )

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
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create paper record
    paper_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        INSERT INTO papers (id, title, authors, status, user_id, storage_key, file_size, keywords,
                           upload_status, upload_progress, uploaded_at, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
        paper_id,
        title,
        [],
        "processing",
        user_id,
        storage_key,
        file_size,
        [],
        "completed",
        100,
        now,
        now,
        now,
    )

    # Create upload history record
    upload_history_id = str(uuid.uuid4())
    await postgres_db.execute(
        """
        INSERT INTO upload_history (id, user_id, paper_id, filename, status, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        upload_history_id,
        user_id,
        paper_id,
        filename,
        "PROCESSING",
        now,
        now,
    )

    # Create processing task
    task_id = str(uuid.uuid4())
    await postgres_db.execute(
        """
        INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        paper_id,
        "pending",
        storage_key,
        now,
        now,
    )

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
):
    """Create a batch upload session.

    Request body:
        files: Array of file info objects

    Returns:
        Batch ID and presigned URLs for each file.
    """
    instance = str(request.url.path)
    user_id = current_user.id
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

    await postgres_db.execute(
        """
        INSERT INTO paper_batches (id, user_id, total_files, uploaded_count, status, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        batch_id,
        user_id,
        len(files),
        0,
        "uploading",
        now,
        now,
    )

    # Create paper records and generate upload URLs
    papers = []
    for file_info in files:
        paper_id = str(uuid.uuid4())
        filename = file_info["filename"]
        title = file_info.get("title") or filename.replace(".pdf", "")
        storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"

        # Create paper record
        await postgres_db.execute(
            """
            INSERT INTO papers (id, user_id, batch_id, title, authors, storage_key, file_size, doi,
                               status, upload_status, upload_progress, keywords, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            paper_id,
            user_id,
            batch_id,
            title,
            [],
            storage_key,
            file_info.get("fileSize"),
            file_info.get("doi"),
            "pending",
            "pending",
            0,
            [],
            now,
            now,
        )

        # Generate upload URL (local storage)
        upload_url = f"/api/v1/uploads/local/{storage_key}"

        papers.append({
            "id": paper_id,
            "uploadUrl": upload_url,
            "filename": filename,
        })

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
):
    """Get batch status.

    Path parameters:
        batch_id: Batch ID

    Returns:
        Batch information.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    batch = await postgres_db.fetchrow(
        "SELECT * FROM paper_batches WHERE id = $1 AND user_id = $2",
        batch_id,
        user_id,
    )

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
        data=dict(batch),
    )


@router.get("/batch/{batch_id}/progress", response_model=UploadResponse)
async def get_batch_progress(
    request: Request,
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed batch progress.

    Path parameters:
        batch_id: Batch ID

    Returns:
        Detailed progress information for all files in batch.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query batch
    batch = await postgres_db.fetchrow(
        "SELECT * FROM paper_batches WHERE id = $1 AND user_id = $2",
        batch_id,
        user_id,
    )

    if not batch:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Batch not found",
            instance=instance,
        )

    # Query papers with processing tasks
    papers = await postgres_db.fetch(
        """
        SELECT p.id, p.title, p.upload_status, p.upload_progress, p.uploaded_at,
               pt.status as processing_status,
               pt.error_message,
               pt.updated_at as last_updated
        FROM papers p
        LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
        WHERE p.batch_id = $1
        ORDER BY p.created_at
        """,
        batch_id,
    )

    # Calculate statistics
    uploaded_count = sum(1 for p in papers if p["upload_status"] == "completed")
    processing_count = sum(1 for p in papers if p["processing_status"] not in ("completed", "failed", "pending", None))
    completed_count = sum(1 for p in papers if p["processing_status"] == "completed")
    failed_count = sum(1 for p in papers if p["processing_status"] == "failed")

    total_files = batch["total_files"]

    # Calculate overall progress: upload (20%) + processing (80%)
    upload_progress = int((uploaded_count / total_files) * 20) if total_files > 0 else 0
    processing_progress = int((completed_count / total_files) * 80) if total_files > 0 else 0
    overall_progress = upload_progress + processing_progress

    # Format per-file progress
    formatted_papers = []
    for paper in papers:
        processing_status = paper["processing_status"] or "pending"
        formatted_papers.append({
            "id": paper["id"],
            "filename": paper["title"] or "Untitled",
            "uploadStatus": paper["upload_status"] or "pending",
            "uploadProgress": paper["upload_progress"] or 0,
            "processingStatus": processing_status,
            "processingProgress": _get_progress_percent(processing_status),
            "processingStage": _get_processing_stage(processing_status),
            "errorMessage": paper["error_message"],
            "uploadedAt": paper["uploaded_at"].isoformat() if paper["uploaded_at"] else None,
        })

    return UploadResponse(
        success=True,
        data={
            "batchId": batch_id,
            "totalFiles": total_files,
            "status": batch["status"],
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
    user_id = current_user.id

    # Verify batch exists
    batch = await postgres_db.fetchrow(
        "SELECT id, total_files, uploaded_count FROM paper_batches WHERE id = $1 AND user_id = $2",
        batch_id,
        user_id,
    )

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
    pending_paper = await postgres_db.fetchrow(
        """
        SELECT id FROM papers
        WHERE batch_id = $1 AND user_id = $2 AND upload_status = 'pending'
        LIMIT 1
        """,
        batch_id,
        user_id,
    )

    if pending_paper:
        # Update existing paper
        paper_id = pending_paper["id"]
        now = datetime.now(timezone.utc)

        await postgres_db.execute(
            """
            UPDATE papers SET
                title = $1,
                storage_key = $2,
                file_size = $3,
                upload_status = 'completed',
                upload_progress = 100,
                uploaded_at = $4,
                updated_at = $5
            WHERE id = $6
            """,
            filename.replace(".pdf", ""),
            storage_key,
            file_size,
            now,
            now,
            paper_id,
        )
    else:
        # Create new paper
        paper_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await postgres_db.execute(
            """
            INSERT INTO papers (id, user_id, batch_id, title, authors, storage_key, file_size,
                               status, upload_status, upload_progress, keywords, uploaded_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            paper_id,
            user_id,
            batch_id,
            filename.replace(".pdf", ""),
            [],
            storage_key,
            file_size,
            "pending",
            "completed",
            100,
            [],
            now,
            now,
            now,
        )

    # Increment batch uploaded count
    new_count = batch["uploaded_count"] + 1
    await postgres_db.execute(
        """
        UPDATE paper_batches SET uploaded_count = $1, updated_at = $2 WHERE id = $3
        """,
        new_count,
        datetime.now(timezone.utc),
        batch_id,
    )

    # If all files uploaded, update status and trigger processing
    if new_count >= batch["total_files"]:
        await postgres_db.execute(
            """
            UPDATE paper_batches SET status = 'processing', updated_at = $1 WHERE id = $2
            """,
            datetime.now(timezone.utc),
            batch_id,
        )

        # Create processing tasks for all pending papers
        pending_papers = await postgres_db.fetch(
            """
            SELECT id, storage_key FROM papers
            WHERE batch_id = $1 AND status = 'pending'
            """,
            batch_id,
        )

        for paper in pending_papers:
            task_id = str(uuid.uuid4())
            await postgres_db.execute(
                """
                INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                task_id,
                paper["id"],
                "pending",
                paper["storage_key"],
                now,
                now,
            )

            await postgres_db.execute(
                """
                UPDATE papers SET status = 'processing', updated_at = $1 WHERE id = $2
                """,
                now,
                paper["id"],
            )

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
            "totalFiles": batch["total_files"],
        },
    )


@router.get("/history", response_model=UploadResponse)
async def get_upload_history(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """Get upload history for user.

    Query parameters:
        limit: Items per page (default 50, max 100)
        offset: Offset for pagination

    Returns:
        List of upload history records.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Validate pagination
    limit = min(100, max(1, limit))
    offset = max(0, offset)

    # Query upload history
    records = await postgres_db.fetch(
        """
        SELECT uh.*,
               p.title as paper_title,
               p.status as paper_status
        FROM upload_history uh
        LEFT JOIN papers p ON uh.paper_id = p.id
        WHERE uh.user_id = $1
        ORDER BY uh.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id,
        limit,
        offset,
    )

    # Get total count
    total_result = await postgres_db.fetchrow(
        "SELECT COUNT(*) as count FROM upload_history WHERE user_id = $1",
        user_id,
    )
    total = total_result["count"] if total_result else 0

    return UploadResponse(
        success=True,
        data={
            "records": [dict(r) for r in records],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.post("/history", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def record_external_upload(
    request: Request,
    body: ExternalUrlUpload,
    current_user: User = Depends(get_current_user),
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
    user_id = current_user.id

    # Create upload history record
    upload_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        INSERT INTO upload_history (id, user_id, filename, status, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        upload_id,
        user_id,
        body.title,
        "EXTERNAL",
        now,
        now,
    )

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
):
    """Delete an upload history record.

    Path parameters:
        upload_id: Upload history ID

    Returns:
        Success message.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify record exists and belongs to user
    record = await postgres_db.fetchrow(
        "SELECT id, paper_id FROM upload_history WHERE id = $1 AND user_id = $2",
        upload_id,
        user_id,
    )

    if not record:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Upload history record not found",
            instance=instance,
        )

    # Delete record (paper is preserved)
    await postgres_db.execute(
        "DELETE FROM upload_history WHERE id = $1",
        upload_id,
    )

    logger.info(
        "Upload history deleted",
        user_id=user_id,
        upload_id=upload_id,
        paper_preserved=record["paper_id"] is not None,
    )

    return UploadResponse(
        success=True,
        data={
            "message": "Upload history record deleted successfully",
            "paperPreserved": record["paper_id"] is not None,
        },
    )


__all__ = ["router"]