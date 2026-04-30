"""Task management service layer.

Provides task management for PDF processing:
- get_task: Get task with ownership check
- list_tasks: List tasks with filters
- create_task: Create processing task
- update_task_status: Update task status and progress
- retry_task: Reset task for retry
- cancel_task: Cancel runnable task
- get_progress_stages: Get PDF processing stage definitions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paper import Paper
from app.models.task import ProcessingTask
from app.utils.logger import logger


PROGRESS_STAGES = {
    "upload": {
        "name": "upload",
        "label": "上传中",
        "label_en": "Uploading",
        "start": 0,
        "end": 15,
        "description": "上传文件到存储",
    },
    "parsing": {
        "name": "parsing",
        "label": "解析中",
        "label_en": "Parsing",
        "start": 15,
        "end": 60,
        "description": "PDF解析和文本提取",
    },
    "indexing": {
        "name": "indexing",
        "label": "索引中",
        "label_en": "Indexing",
        "start": 60,
        "end": 90,
        "description": "向量索引和存储",
    },
    "multimodal": {
        "name": "multimodal",
        "label": "多模态处理",
        "label_en": "Multimodal Processing",
        "start": 90,
        "end": 100,
        "description": "图片表格提取与索引",
    },
}


class TaskService:
    @staticmethod
    async def get_task(db: AsyncSession, task_id: str, user_id: str) -> Optional[ProcessingTask]:
        query = (
            select(ProcessingTask)
            .options(selectinload(ProcessingTask.paper))
            .join(Paper, ProcessingTask.paper_id == Paper.id)
            .where(ProcessingTask.id == task_id, Paper.user_id == user_id)
        )
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            logger.warning("Task not found or not owned", task_id=task_id, user_id=user_id)
            raise ValueError("Task not found")
        return task

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        user_id: str,
        paper_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ProcessingTask]:
        query = (
            select(ProcessingTask)
            .options(selectinload(ProcessingTask.paper))
            .join(Paper, ProcessingTask.paper_id == Paper.id)
            .where(Paper.user_id == user_id)
            .order_by(ProcessingTask.created_at.desc())
        )
        if paper_id:
            query = query.where(ProcessingTask.paper_id == paper_id)
        if status:
            query = query.where(ProcessingTask.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: str,
        paper_id: str,
        task_type: str = "pdf_processing",
        storage_key: Optional[str] = None,
    ) -> ProcessingTask:
        paper_query = select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        paper_result = await db.execute(paper_query)
        paper = paper_result.scalar_one_or_none()
        if not paper:
            raise ValueError("Paper not found or not owned by user")

        now = datetime.now(timezone.utc)
        task = ProcessingTask(
            id=str(uuid4()),
            paper_id=paper_id,
            task_type=task_type,
            status="pending",
            storage_key=storage_key or paper.storage_key,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        await db.flush()
        return task

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ProcessingTask:
        query = select(ProcessingTask).where(ProcessingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")

        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if error_message:
            task.error_message = error_message
            task.failure_message = error_message
        if status == "completed":
            task.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return task

    @staticmethod
    async def retry_task(db: AsyncSession, task_id: str, user_id: str) -> ProcessingTask:
        task = await TaskService.get_task(db, task_id, user_id)
        if task.status != "failed":
            raise ValueError("Only failed tasks can be retried")
        if not task.is_retryable:
            raise PermissionError("Task is not retryable")

        now = datetime.now(timezone.utc)
        retry_trace_id = str(uuid4())
        task.status = "pending"
        task.attempts = (task.attempts or 0) + 1
        task.error_message = None
        task.failure_message = None
        task.failure_code = None
        task.failure_stage = None
        task.completed_at = None
        task.cancelled_at = None
        task.cancellation_reason = None
        task.retry_trace_id = retry_trace_id
        task.trace_id = retry_trace_id
        task.updated_at = now
        if task.paper:
            task.paper.status = "pending"
            task.paper.updated_at = now
        await db.flush()

        logger.info(
            "Task reset for retry",
            task_id=task_id,
            user_id=user_id,
            attempts=task.attempts,
            retry_trace_id=retry_trace_id,
        )
        return task

    @staticmethod
    async def cancel_task(db: AsyncSession, task_id: str, user_id: str) -> ProcessingTask:
        task = await TaskService.get_task(db, task_id, user_id)
        if task.status in {"completed", "failed", "cancelled"}:
            raise RuntimeError(f"Cannot cancel task in status: {task.status}")

        now = datetime.now(timezone.utc)
        task.status = "cancelled"
        task.cancelled_at = now
        task.cancellation_reason = "user_request"
        task.failure_stage = "cancelled"
        task.failure_code = "user_cancelled"
        task.failure_message = "Task cancelled by user"
        task.updated_at = now
        if task.paper:
            task.paper.status = "cancelled"
            task.paper.updated_at = now
        await db.flush()

        logger.info("Task cancelled", task_id=task_id, user_id=user_id)
        return task

    @staticmethod
    def get_progress_stages() -> Dict[str, Dict[str, Any]]:
        return PROGRESS_STAGES.copy()

    @staticmethod
    def calculate_progress(current_stage: str, stage_progress: float = 0.0) -> int:
        stages = TaskService.get_progress_stages()
        if current_stage not in stages:
            return 0
        stage = stages[current_stage]
        stage_range = stage["end"] - stage["start"]
        overall = stage["start"] + (stage_range * stage_progress)
        return min(100, max(0, int(overall)))


__all__ = ["TaskService"]
