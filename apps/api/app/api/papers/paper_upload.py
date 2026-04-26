"""Paper upload operations - webhook and direct upload.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- POST /api/v1/papers/webhook - Confirm upload completion (compat shim → ImportJob-first)
- POST /api/v1/papers/upload - Direct file upload (compat shim → ImportJob-first)
- POST /api/v1/papers/upload/local/{storage_key} - Local storage file upload

NOTE: Both /webhook and /upload are legacy compatibility endpoints.
Internally they now delegate to create_import_job_from_uploaded_file() so that
all uploads go through the canonical ImportJob-first pipeline.
"""

import aiofiles

from fastapi import APIRouter, Depends, Request, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Paper, ImportJob
from app.services.auth_service import User
from app.services.import_file_service import (
    create_import_job_from_uploaded_file,
    read_uploaded_pdf,
)
from app.utils.problem_detail import ErrorTypes

from .paper_shared import (
    PaperCreateResponse,
    WebhookRequest,
    create_error_response,
    datetime,
    timezone,
    uuid4,
    logger,
)


router = APIRouter()


@router.post(
    "/webhook", response_model=PaperCreateResponse, status_code=status.HTTP_200_OK
)
async def upload_webhook(
    request: Request,
    body: WebhookRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Legacy compatibility shim: confirm file upload.

    Previously created ProcessingTask directly.  Now finds the ImportJob that
    owns this paper and returns its current state.  Does NOT create any new
    database records.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    paper_id = body.paperId
    storage_key = body.storageKey

    if not paper_id or not storage_key:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="paperId and storageKey are required",
            instance=instance,
        )

    # Find the ImportJob that materialised this paper
    job_result = await db.execute(
        select(ImportJob).where(
            ImportJob.paper_id == paper_id,
            ImportJob.user_id == user_id,
        )
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="No ImportJob found for this paper",
            instance=instance,
        )

    logger.info(
        "Webhook compat shim: returning ImportJob state",
        import_job_id=job.id,
        paper_id=paper_id,
        status=job.status,
    )

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": paper_id,
            "taskId": job.id,
            "importJobId": job.id,
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress or 0,
        },
    )


@router.post(
    "/upload", response_model=PaperCreateResponse, status_code=status.HTTP_202_ACCEPTED
)
async def direct_upload(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Legacy compatibility shim: direct file upload.

    Previously created Paper + ProcessingTask directly.  Now delegates to the
    unified ImportJob-first helper so all uploads go through the canonical
    pipeline: Upload → ImportJob → ProcessingTask → PDFCoordinator.

    Response shape is backward-compatible: paperId is null until ImportJob
    materialises the Paper; callers should poll /import-jobs/{importJobId}.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    try:
        content, filename = await read_uploaded_pdf(file)
    except ValueError as exc:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail=str(exc),
            instance=instance,
        )

    result = await create_import_job_from_uploaded_file(
        user_id=user_id,
        filename=filename,
        content=content,
        db=db,
    )

    logger.info(
        "Legacy /papers/upload routed to ImportJob-first",
        import_job_id=result["importJobId"],
        user_id=user_id,
    )

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": None,
            "taskId": result["importJobId"],
            "importJobId": result["importJobId"],
            "status": result["status"],
            "stage": result["stage"],
            "progress": result["progress"],
        },
    )


class LocalUploadResponse(BaseModel):
    """Response for local storage file upload."""

    success: bool = True
    data: dict


@router.post(
    "/upload/local/{storage_key:path}",
    response_model=LocalUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_to_local_storage(
    request: Request,
    storage_key: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload file to local storage at specified storage_key path.

    This endpoint handles the second step of the upload flow:
    1. POST /api/v1/papers -> creates paper record, returns uploadUrl
    2. POST /api/v1/papers/upload/local/{storage_key} -> uploads file (this endpoint)
    3. POST /api/v1/papers/webhook -> triggers processing

    Args:
        storage_key: Path within uploads directory (e.g., user_id/date/file.pdf)
        file: PDF file to upload

    Returns:
        Storage key and file size on success
    """
    instance = str(request.url.path)
    user_id = current_user.id

    if not storage_key.startswith(str(user_id) + "/"):
        raise create_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            error_type=ErrorTypes.FORBIDDEN,
            title="Forbidden",
            detail="Storage key does not belong to current user",
            instance=instance,
        )

    if ".." in storage_key or storage_key.startswith("/"):
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Invalid storage key format",
            instance=instance,
        )

    if not file:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="No file uploaded",
            instance=instance,
        )

    content = await file.read()
    file_size = len(content)

    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise create_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_type=ErrorTypes.FILE_TOO_LARGE,
            title="File Too Large",
            detail="File size exceeds 50MB limit",
            instance=instance,
        )

    if not content.startswith(b"%PDF-"):
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="File is not a valid PDF",
            instance=instance,
        )

    local_storage_path = settings.LOCAL_STORAGE_PATH
    file_path = f"{local_storage_path}/{storage_key}"

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(
        "File uploaded to local storage",
        user_id=user_id,
        storage_key=storage_key,
        file_size=file_size,
    )

    return LocalUploadResponse(
        success=True,
        data={
            "storageKey": storage_key,
            "size": file_size,
            "message": "File uploaded successfully",
        },
    )


__all__ = ["router"]
