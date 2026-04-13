"""Paper status and metadata operations.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- GET /api/v1/papers/{id}/status - Get processing status
- PATCH /api/v1/papers/{id}/starred - Toggle starred
- GET /api/v1/papers/{id}/download - Download PDF
- GET /api/v1/papers/{id}/chunks - Get paper chunks
- POST /api/v1/papers/{id}/regenerate-chunks - Regenerate chunks
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models import Paper, ProcessingTask, PaperChunk
from app.services.auth_service import User
from app.utils.problem_detail import ErrorTypes

from .paper_shared import (
    StarredRequest,
    create_error_response,
    get_progress_percent,
    get_processing_stage,
    format_paper_response,
    datetime,
    timezone,
    uuid4,
    logger,
)


router = APIRouter()


@router.get("/{paper_id}/status")
async def get_paper_status(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get paper processing status."""
    instance = str(request.url.path)
    user_id = current_user.id

    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.id == paper_id)
        .where(Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper, task = row

    processing_status = task.status if task else paper.status or "pending"
    progress = get_progress_percent(processing_status)
    stage = get_processing_stage(processing_status)

    return {
        "success": True,
        "data": {
            "paperId": paper_id,
            "status": processing_status,
            "progress": progress,
            "stage": stage,
            "errorMessage": task.error_message if task else None,
            "storageKey": paper.storage_key,
        },
    }


@router.patch("/{paper_id}/starred")
async def toggle_starred(
    request: Request,
    paper_id: str,
    body: StarredRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Toggle paper starred status."""
    instance = str(request.url.path)
    user_id = current_user.id

    existing_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    existing_result = await db.execute(existing_query)
    paper = existing_result.scalar_one_or_none()

    if not paper:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper.starred = body.starred
    paper.updated_at = datetime.now(timezone.utc)
    await db.refresh(paper)

    return {"success": True, "data": format_paper_response(paper)}


@router.get("/{paper_id}/download")
async def download_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Download paper PDF file."""
    instance = str(request.url.path)
    user_id = current_user.id

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

    storage_key = paper.storage_key
    if not storage_key:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="No file associated with this paper",
            instance=instance,
        )

    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    if not os.path.exists(file_path):
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="File not found in storage",
            instance=instance,
        )

    filename = f"{paper.title or 'paper'}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/{paper_id}/chunks")
async def get_paper_chunks(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get paper chunks for reading."""
    instance = str(request.url.path)
    user_id = current_user.id

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

    chunks_query = (
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.page_start, PaperChunk.id)
    )
    chunks_result = await db.execute(chunks_query)
    chunks = chunks_result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": c.id,
                "content": c.content,
                "section": c.section,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "is_table": c.is_table,
                "is_figure": c.is_figure,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chunks
        ],
    }


@router.post("/{paper_id}/regenerate-chunks")
async def regenerate_chunks(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger chunk regeneration for a paper."""
    instance = str(request.url.path)
    user_id = current_user.id

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

    now = datetime.now(timezone.utc)

    if existing_task:
        existing_task.status = "pending"
        existing_task.error_message = None
        existing_task.updated_at = now
        task_id = existing_task.id
    else:
        task_id = str(uuid4())
        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=paper.storage_key,
            created_at=now,
            updated_at=now,
        )
        db.add(task)

    return {
        "success": True,
        "data": {
            "taskId": task_id,
            "message": "Chunk regeneration triggered",
        },
    }


__all__ = ["router"]
