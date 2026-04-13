"""Paper upload operations - webhook and direct upload.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- POST /api/v1/papers/webhook - Confirm upload completion
- POST /api/v1/papers/upload - Direct file upload
"""

import os
import aiofiles

from fastapi import APIRouter, Depends, Request, UploadFile, File, status
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models import Paper, ProcessingTask, UploadHistory
from app.services.auth_service import User
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
    "/webhook", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED
)
async def upload_webhook(
    request: Request,
    body: WebhookRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Confirm file upload and create processing task."""
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

    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    existing_task_query = select(ProcessingTask).where(
        ProcessingTask.paper_id == paper_id,
    )
    existing_task_result = await db.execute(existing_task_query)
    existing_task = existing_task_result.scalar_one_or_none()

    if existing_task:
        raise create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Conflict",
            detail="Processing task already exists for this paper",
            instance=instance,
        )

    task_id = str(uuid4())
    now = datetime.now(timezone.utc)

    task = ProcessingTask(
        id=task_id,
        paper_id=paper_id,
        status="pending",
        storage_key=storage_key,
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    paper.status = "processing"
    paper.upload_status = "completed"
    paper.upload_progress = 100
    paper.uploaded_at = now
    paper.updated_at = now

    return PaperCreateResponse(
        success=True,
        data={
            "taskId": task_id,
            "paperId": paper_id,
            "status": "pending",
            "progress": 0,
        },
    )


@router.post(
    "/upload", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED
)
async def direct_upload(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Direct file upload endpoint."""
    instance = str(request.url.path)
    user_id = current_user.id

    if not file:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="No file uploaded",
            instance=instance,
        )

    filename = file.filename or "untitled.pdf"

    if not filename.lower().endswith(".pdf"):
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only PDF files are accepted",
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

    title = filename.replace(".pdf", "").replace(".PDF", "")

    existing_query = select(Paper).where(
        Paper.user_id == user_id,
        Paper.title == title,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists',
            instance=instance,
        )

    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid4()}.pdf"
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    paper_id = str(uuid4())
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
        upload_status="completed",
        upload_progress=100,
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(paper)

    task_id = str(uuid4())

    task = ProcessingTask(
        id=task_id,
        paper_id=paper_id,
        status="pending",
        storage_key=storage_key,
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": paper_id,
            "taskId": task_id,
            "status": "processing",
        },
    )


__all__ = ["router"]
