"""Task management API routes.

Provides task querying and control for PDF processing and long-running jobs.
"""

from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.routing import Router as StarletteRouter

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.task_service import TaskService

if "on_startup" not in inspect.signature(StarletteRouter.__init__).parameters:
    _original_starlette_router_init = StarletteRouter.__init__

    def _compat_starlette_router_init(self, *args, on_startup=None, on_shutdown=None, **kwargs):
        return _original_starlette_router_init(self, *args, **kwargs)

    StarletteRouter.__init__ = _compat_starlette_router_init

router = APIRouter(tags=["tasks"])
if not hasattr(router, "on_startup"):
    router.on_startup = []
if not hasattr(router, "on_shutdown"):
    router.on_shutdown = []


class TaskListItem(BaseModel):
    id: str
    paper_id: str
    paper_title: Optional[str] = None
    task_type: str
    status: str
    currentStage: str
    progress: int
    attempts: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    trace_id: Optional[str] = None


class TaskDetailResponse(BaseModel):
    id: str
    paper_id: str
    paper_title: Optional[str] = None
    task_type: str
    status: str
    currentStage: str
    progress: int
    attempts: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    checkpoint_stage: Optional[str] = None
    checkpoint_storage_key: Optional[str] = None
    checkpoint_version: int = 0
    stage_timings: Dict[str, Any] = Field(default_factory=dict)
    failure_stage: Optional[str] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    is_retryable: bool = True
    trace_id: Optional[str] = None
    retry_trace_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)
    cache_stats: Dict[str, Any] = Field(default_factory=dict)
    queue_wait_ms: Optional[int] = None


class APIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None


def _resolve_stage(task) -> str:
    if task.status == "completed":
        return "completed"
    if task.status == "failed":
        return task.failure_stage or task.checkpoint_stage or "failed"
    if task.status == "cancelled":
        return "cancelled"
    return task.checkpoint_stage or task.status or "pending"


def _resolve_progress(task) -> int:
    stage = _resolve_stage(task)
    if task.status == "completed":
        return 100
    stage_progress = 0.0
    if task.status == "failed" and task.failure_stage:
        stage_progress = 1.0
    if task.status == "cancelled":
        stage_progress = 0.0
    if stage in TaskService.get_progress_stages():
        return TaskService.calculate_progress(stage, stage_progress)
    if stage == "completed":
        return 100
    return 0


def _task_list_item(task) -> TaskListItem:
    return TaskListItem(
        id=task.id,
        paper_id=task.paper_id,
        paper_title=getattr(task.paper, "title", None),
        task_type=task.task_type or "pdf_processing",
        status=task.status,
        currentStage=_resolve_stage(task),
        progress=_resolve_progress(task),
        attempts=task.attempts or 0,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        trace_id=task.trace_id,
    )


def _task_detail(task) -> TaskDetailResponse:
    return TaskDetailResponse(
        id=task.id,
        paper_id=task.paper_id,
        paper_title=getattr(task.paper, "title", None),
        task_type=task.task_type or "pdf_processing",
        status=task.status,
        currentStage=_resolve_stage(task),
        progress=_resolve_progress(task),
        attempts=task.attempts or 0,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        checkpoint_stage=task.checkpoint_stage,
        checkpoint_storage_key=task.checkpoint_storage_key,
        checkpoint_version=task.checkpoint_version or 0,
        stage_timings=task.stage_timings or {},
        failure_stage=task.failure_stage,
        failure_code=task.failure_code,
        failure_message=task.failure_message,
        is_retryable=bool(task.is_retryable),
        trace_id=task.trace_id,
        retry_trace_id=task.retry_trace_id,
        cancelled_at=task.cancelled_at,
        cancellation_reason=task.cancellation_reason,
        cost_breakdown=task.cost_breakdown or {},
        cache_stats=task.cache_stats or {},
        queue_wait_ms=task.queue_wait_ms,
    )


@router.get("", response_model=APIResponse)
async def list_tasks(
    paper_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await TaskService.list_tasks(db, current_user.id, paper_id=paper_id, status=status_filter)
    items = [_task_list_item(task).model_dump() for task in tasks]
    return APIResponse(success=True, data={"tasks": items, "total": len(items)})


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = await TaskService.get_task(db, task_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return APIResponse(success=True, data=_task_detail(task).model_dump())


@router.get("/{task_id}/progress", response_model=APIResponse)
async def get_task_progress(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = await TaskService.get_task(db, task_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    stages = []
    current_stage = _resolve_stage(task)
    current_progress = _resolve_progress(task)
    for key, stage in TaskService.get_progress_stages().items():
        stage_status = "completed" if current_progress >= stage["end"] else "pending"
        if current_stage == key and task.status not in {"completed", "failed", "cancelled"}:
            stage_status = "active"
        stages.append({**stage, "status": stage_status})

    data = {
        "task_id": task.id,
        "status": task.status,
        "currentStage": current_stage,
        "progress": current_progress,
        "stages": stages,
        "error_message": task.error_message,
        "updated_at": task.updated_at,
    }
    return APIResponse(success=True, data=data)


@router.post("/{task_id}/retry", response_model=APIResponse)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = await TaskService.retry_task(db, task_id, current_user.id)
        await db.commit()
        await db.refresh(task)
    except ValueError as exc:
        await db.rollback()
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message == "Task not found" else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=message) from exc
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return APIResponse(
        success=True,
        message="Task queued for retry",
        data={
            "id": task.id,
            "status": task.status,
            "attempts": task.attempts,
            "retry_trace_id": task.retry_trace_id,
            "recovery": {
                "checkpoint_stage": task.checkpoint_stage,
                "checkpoint_version": task.checkpoint_version,
                "retry_trace_id": task.retry_trace_id,
            },
        },
    )


@router.delete("/{task_id}", response_model=APIResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = await TaskService.cancel_task(db, task_id, current_user.id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return APIResponse(
        success=True,
        message="Task cancelled",
        data={
            "id": task.id,
            "status": task.status,
            "cancelled_at": task.cancelled_at,
            "cancellation_reason": task.cancellation_reason,
            "cancellation_requested": True,
        },
    )
