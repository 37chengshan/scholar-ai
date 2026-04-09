"""Task management API routes.

Migrated from Node.js tasks.ts - provides endpoints for PDF processing task management.

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

from app.deps import get_current_user, postgres_db
from app.services.auth_service import User
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


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

    # Build query conditions
    conditions = ["p.user_id = $1"]
    params = [user_id]
    param_idx = 2

    if paperId:
        conditions.append(f"pt.paper_id = ${param_idx}")
        params.append(paperId)
        param_idx += 1

    if status_filter:
        conditions.append(f"pt.status = ${param_idx}")
        params.append(status_filter)
        param_idx += 1

    where_sql = " AND ".join(conditions)

    # Query tasks with paper info
    query = f"""
        SELECT pt.id, pt.paper_id, pt.status, pt.storage_key, pt.error_message,
               pt.attempts, pt.created_at, pt.updated_at, pt.completed_at,
               p.title as paper_title
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE {where_sql}
        ORDER BY pt.created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])

    tasks = await postgres_db.fetch(query, *params)

    # Get total count
    count_query = f"""
        SELECT COUNT(*) as count
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE {where_sql}
    """
    count_params = params[:-2]  # Remove limit and offset
    total_result = await postgres_db.fetchrow(count_query, *count_params)
    total = total_result["count"] if total_result else 0

    # Format response
    formatted_tasks = []
    for task in tasks:
        task_dict = dict(task)
        stage_info = _get_stage_progress(task_dict["status"])
        task_dict["currentStage"] = stage_info["stage"]
        task_dict["progress"] = stage_info["progress"]
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
    task = await postgres_db.fetchrow(
        """
        SELECT pt.*, p.title as paper_title, p.user_id
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE pt.id = $1 AND p.user_id = $2
        """,
        task_id,
        user_id,
    )

    if not task:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    task_dict = dict(task)
    stage_info = _get_stage_progress(task_dict["status"])
    task_dict["currentStage"] = stage_info["stage"]
    task_dict["progress"] = stage_info["progress"]

    return TaskResponse(success=True, data=task_dict)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
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
    task = await postgres_db.fetchrow(
        """
        SELECT pt.id, pt.status, pt.paper_id, p.user_id
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE pt.id = $1 AND p.user_id = $2
        """,
        task_id,
        user_id,
    )

    if not task:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    if task["status"] != "failed":
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only failed tasks can be retried",
            instance=instance,
        )

    # Reset task status
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        UPDATE processing_tasks
        SET status = 'pending',
            error_message = NULL,
            attempts = attempts + 1,
            updated_at = $1
        WHERE id = $2
        """,
        now,
        task_id,
    )

    # Reset paper status
    await postgres_db.execute(
        """
        UPDATE papers SET status = 'pending', updated_at = $1 WHERE id = $2
        """,
        now,
        task["paper_id"],
    )

    logger.info(
        "Task retry triggered",
        user_id=user_id,
        task_id=task_id,
        paper_id=task["paper_id"],
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
    task = await postgres_db.fetchrow(
        """
        SELECT pt.*, p.title as paper_title, p.page_count
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE pt.id = $1 AND p.user_id = $2
        """,
        task_id,
        user_id,
    )

    if not task:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    # Get stages
    stages = _get_progress_stages()
    current_stage_info = _get_stage_progress(task["status"])
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
            "taskId": task["id"],
            "paperId": task["paper_id"],
            "paperTitle": task["paper_title"],
            "status": task["status"],
            "progress": overall_progress,
            "currentStage": current_stage,
            "stages": formatted_stages,
            "errorMessage": task["error_message"],
            "attempts": task["attempts"],
            "pageCount": task["page_count"],
            "createdAt": task["created_at"].isoformat() if task["created_at"] else None,
            "updatedAt": task["updated_at"].isoformat() if task["updated_at"] else None,
            "completedAt": task["completed_at"].isoformat() if task["completed_at"] else None,
        },
    )


@router.delete("/{task_id}")
async def cancel_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
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
    task = await postgres_db.fetchrow(
        """
        SELECT pt.id, pt.status, pt.paper_id, p.user_id
        FROM processing_tasks pt
        JOIN papers p ON pt.paper_id = p.id
        WHERE pt.id = $1 AND p.user_id = $2
        """,
        task_id,
        user_id,
    )

    if not task:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Task not found",
            instance=instance,
        )

    if task["status"] != "pending":
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only pending tasks can be cancelled",
            instance=instance,
        )

    # Delete task
    await postgres_db.execute(
        "DELETE FROM processing_tasks WHERE id = $1",
        task_id,
    )

    # Update paper status
    await postgres_db.execute(
        """
        UPDATE papers SET status = 'cancelled', updated_at = $1 WHERE id = $2
        """,
        datetime.now(timezone.utc),
        task["paper_id"],
    )

    logger.info(
        "Task cancelled",
        user_id=user_id,
        task_id=task_id,
        paper_id=task["paper_id"],
    )

    return TaskResponse(
        success=True,
        data={
            "message": "Task cancelled successfully",
            "taskId": task_id,
        },
    )


__all__ = ["router"]