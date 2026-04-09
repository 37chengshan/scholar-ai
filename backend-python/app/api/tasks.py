"""Task management API routes.

Migrated from Node.js tasks.ts - provides endpoints for PDF processing task management.
Migrated to SQLAlchemy ORM from postgres_db.

Endpoints:
- GET /api/v1/tasks - List tasks for user's papers
- GET /api/v1/tasks/:id - Get task details
- POST /api/v1/tasks/:id/retry - Retry failed task
- GET /api/v1/tasks/:id/progress - Get detailed progress
- DELETE /api/v1/tasks/:id - Cancel pending task
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import ProcessingTask, Paper
from app.services.auth_service import User
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


router = APIRouter(tags=["Tasks"])


# =============================================================================
# Request/Response Models
# =============================================================================

class TaskResponse(BaseModel):
    """Task response."""
    success: bool = True
    data: dict


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


def _get_progress_stages() -> list:
    """Get processing stages with progress percentages."""
    return [
        {"name": "upload", "label": "Uploading", "start": 0, "end": 15, "weight": 15},
        {"name": "parsing", "label": "Parsing Document", "start": 15, "end": 60, "weight": 45},
        {"name": "indexing", "label": "Indexing Content", "start": 60, "end": 90, "weight": 30},
        {"name": "multimodal", "label": "Processing Multimodal", "start": 90, "end": 100, "weight": 10},
    ]


def _get_stage_progress(status: str) -> dict:
    """Get current stage and progress for a task status."""
    stage_map = {
        "pending": {"stage": "upload", "progress": 0},
        "processing_ocr": {"stage": "parsing", "progress": 20},
        "parsing": {"stage": "parsing", "progress": 35},
        "extracting_imrad": {"stage": "parsing", "progress": 50},
        "generating_notes": {"stage": "indexing", "progress": 65},
        "storing_vectors": {"stage": "indexing", "progress": 80},
        "indexing_multimodal": {"stage": "multimodal", "progress": 95},
        "completed": {"stage": "completed", "progress": 100},
        "failed": {"stage": "failed", "progress": 0},
    }
    return stage_map.get(status, {"stage": "pending", "progress": 0})


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=TaskResponse)
async def list_tasks(
    request: Request,
    paperId: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks for user's papers.

    Query parameters:
        paperId: Filter by paper ID
        status: Filter by task status
        limit: Items per page
        offset: Offset for pagination

    Returns:
        List of tasks with pagination.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Build query with join
    query = (
        select(ProcessingTask, Paper.title)
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(Paper.user_id == user_id)
    )

    if paperId:
        query = query.where(ProcessingTask.paper_id == paperId)

    if status_filter:
        query = query.where(ProcessingTask.status == status_filter)

    # Order by created_at desc and apply pagination
    query = query.order_by(ProcessingTask.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    # Get total count
    count_query = (
        select(func.count(ProcessingTask.id))
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(Paper.user_id == user_id)
    )

    if paperId:
        count_query = count_query.where(ProcessingTask.paper_id == paperId)

    if status_filter:
        count_query = count_query.where(ProcessingTask.status == status_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Format response
    formatted_tasks = []
    for task, paper_title in rows:
        stage_info = _get_stage_progress(task.status)
        task_dict = {
            "id": task.id,
            "paper_id": task.paper_id,
            "status": task.status,
            "storage_key": task.storage_key,
            "error_message": task.error_message,
            "attempts": task.attempts,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
            "paper_title": paper_title,
            "currentStage": stage_info["stage"],
            "progress": stage_info["progress"],
        }
        formatted_tasks.append(task_dict)

    return TaskResponse(
        success=True,
        data={
            "tasks": formatted_tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task details.

    Path parameters:
        task_id: Task ID

    Returns:
        Task details with paper info.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query task with user isolation
    query = (
        select(ProcessingTask, Paper.title, Paper.user_id)
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(ProcessingTask.id == task_id, Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    task, paper_title, _ = row
    stage_info = _get_stage_progress(task.status)

    task_dict = {
        "id": task.id,
        "paper_id": task.paper_id,
        "status": task.status,
        "storage_key": task.storage_key,
        "error_message": task.error_message,
        "attempts": task.attempts,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "paper_title": paper_title,
        "currentStage": stage_info["stage"],
        "progress": stage_info["progress"],
    }

    return TaskResponse(success=True, data=task_dict)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed task.

    Path parameters:
        task_id: Task ID

    Returns:
        Updated task status.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify task exists and belongs to user's paper
    query = (
        select(ProcessingTask.id, ProcessingTask.status, ProcessingTask.paper_id, Paper.user_id)
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(ProcessingTask.id == task_id, Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    task_id_val, task_status, paper_id_val, _ = row

    if task_status != "failed":
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only failed tasks can be retried",
            instance=instance,
        )

    # Reset task status
    now = datetime.now(timezone.utc)

    task_update_stmt = (
        update(ProcessingTask)
        .where(ProcessingTask.id == task_id)
        .values(
            status="pending",
            error_message=None,
            attempts=ProcessingTask.attempts + 1,
            updated_at=now,
        )
    )
    await db.execute(task_update_stmt)

    # Reset paper status
    paper_update_stmt = (
        update(Paper)
        .where(Paper.id == paper_id_val)
        .values(status="pending", updated_at=now)
    )
    await db.execute(paper_update_stmt)

    logger.info(
        "Task retry triggered",
        user_id=user_id,
        task_id=task_id,
        paper_id=paper_id_val,
    )

    return TaskResponse(
        success=True,
        data={
            "taskId": task_id,
            "status": "pending",
            "message": "Task retry initiated",
        },
    )


@router.get("/{task_id}/progress", response_model=TaskResponse)
async def get_task_progress(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed task progress with stages.

    Path parameters:
        task_id: Task ID

    Returns:
        Detailed progress information with stages.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query task with user isolation
    query = (
        select(ProcessingTask, Paper.title, Paper.page_count)
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(ProcessingTask.id == task_id, Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    task, paper_title, page_count = row

    # Get stages
    stages = _get_progress_stages()
    current_stage_info = _get_stage_progress(task.status)
    current_stage = current_stage_info["stage"]
    overall_progress = current_stage_info["progress"]

    # Format stages with completion status
    formatted_stages = []
    for stage in stages:
        is_completed = False
        is_current = False

        if current_stage == "completed":
            is_completed = True
        elif current_stage == "failed":
            is_current = stage["name"] == current_stage_info["stage"]
        else:
            stage_order = ["upload", "parsing", "indexing", "multimodal", "completed"]
            current_idx = stage_order.index(current_stage) if current_stage in stage_order else -1
            stage_idx = stage_order.index(stage["name"])

            if stage_idx < current_idx:
                is_completed = True
            elif stage_idx == current_idx:
                is_current = True

        formatted_stages.append({
            "name": stage["name"],
            "label": stage["label"],
            "start": stage["start"],
            "end": stage["end"],
            "weight": stage["weight"],
            "completed": is_completed,
            "current": is_current,
        })

    return TaskResponse(
        success=True,
        data={
            "taskId": task.id,
            "paperId": task.paper_id,
            "paperTitle": paper_title,
            "status": task.status,
            "progress": overall_progress,
            "currentStage": current_stage,
            "stages": formatted_stages,
            "errorMessage": task.error_message,
            "attempts": task.attempts,
            "pageCount": page_count,
            "createdAt": task.created_at.isoformat() if task.created_at else None,
            "updatedAt": task.updated_at.isoformat() if task.updated_at else None,
            "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        },
    )


@router.delete("/{task_id}")
async def cancel_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending task.

    Path parameters:
        task_id: Task ID

    Returns:
        Success message.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify task exists and belongs to user's paper
    query = (
        select(ProcessingTask.id, ProcessingTask.status, ProcessingTask.paper_id, Paper.user_id)
        .join(Paper, ProcessingTask.paper_id == Paper.id)
        .where(ProcessingTask.id == task_id, Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    task_id_val, task_status, paper_id_val, _ = row

    if task_status != "pending":
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only pending tasks can be cancelled",
            instance=instance,
        )

    # Delete task
    delete_stmt = delete(ProcessingTask).where(ProcessingTask.id == task_id)
    await db.execute(delete_stmt)

    # Update paper status
    paper_update_stmt = (
        update(Paper)
        .where(Paper.id == paper_id_val)
        .values(status="cancelled", updated_at=datetime.now(timezone.utc))
    )
    await db.execute(paper_update_stmt)

    logger.info(
        "Task cancelled",
        user_id=user_id,
        task_id=task_id,
        paper_id=paper_id_val,
    )

    return TaskResponse(
        success=True,
        data={
            "message": "Task cancelled successfully",
            "taskId": task_id,
        },
    )


__all__ = ["router"]