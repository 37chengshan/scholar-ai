"""Task management service layer.

Provides task management for PDF processing:
- get_task: Get task with ownership check
- list_tasks: List tasks with filters
- create_task: Create processing task
- update_task_status: Update task status and progress
- retry_task: Reset task for retry
- cancel_task: Cancel pending task
- get_progress_stages: Get PDF processing stage definitions

Per D-04: Service layer for business logic separation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import ProcessingTask
from app.utils.logger import logger


# PDF Processing progress stages
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
    """Service class for task management.

    All methods are async and use SQLAlchemy AsyncSession.
    Includes proper error handling and logging.
    """

    @staticmethod
    async def get_task(
        db: AsyncSession,
        task_id: str,
        user_id: str,
    ) -> Optional[ProcessingTask]:
        """Get a task with ownership check.

        Args:
            db: AsyncSession database connection
            task_id: Task ID
            user_id: User ID (for ownership verification via paper)

        Returns:
            ProcessingTask if found and owned by user

        Raises:
            ValueError: If task not found or not owned by user
        """
        # Join with papers to check ownership
        from app.models.paper import Paper

        query = (
            select(ProcessingTask)
            .join(Paper, ProcessingTask.paper_id == Paper.id)
            .where(
                ProcessingTask.id == task_id,
                Paper.user_id == user_id,
            )
        )

        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            logger.warning(
                "Task not found or not owned",
                task_id=task_id,
                user_id=user_id,
            )
            raise ValueError("Task not found")

        logger.info("Task retrieved", task_id=task_id, user_id=user_id)
        return task

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        user_id: str,
        paper_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ProcessingTask]:
        """List tasks for a user's papers.

        Args:
            db: AsyncSession database connection
            user_id: User ID (owner of papers)
            paper_id: Optional filter by paper
            status: Optional filter by status

        Returns:
            List of ProcessingTask objects
        """
        from app.models.paper import Paper

        # Build query with paper ownership join
        query = (
            select(ProcessingTask)
            .join(Paper, ProcessingTask.paper_id == Paper.id)
            .where(Paper.user_id == user_id)
            .order_by(ProcessingTask.created_at.desc())
        )

        # Apply filters
        if paper_id:
            query = query.where(ProcessingTask.paper_id == paper_id)

        if status:
            query = query.where(ProcessingTask.status == status)

        result = await db.execute(query)
        tasks = result.scalars().all()

        logger.info(
            "Tasks listed",
            user_id=user_id,
            paper_id=paper_id,
            status=status,
            count=len(tasks),
        )

        return list(tasks)

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: str,
        paper_id: str,
        task_type: str = "pdf_processing",
        storage_key: Optional[str] = None,
    ) -> ProcessingTask:
        """Create a new processing task.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for paper ownership verification)
            paper_id: Paper ID to process
            task_type: Type of task (default: pdf_processing)
            storage_key: Storage key for the PDF

        Returns:
            Created ProcessingTask object

        Raises:
            ValueError: If paper not found or not owned by user
        """
        from app.models.paper import Paper

        # Verify paper ownership
        paper_query = select(Paper).where(
            Paper.id == paper_id,
            Paper.user_id == user_id,
        )
        paper_result = await db.execute(paper_query)
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise ValueError("Paper not found or not owned by user")

        # Create task
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)

        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=storage_key or paper.storage_key,
            attempts=0,
            created_at=now,
            updated_at=now,
        )

        db.add(task)
        await db.flush()

        logger.info(
            "Task created",
            task_id=task_id,
            paper_id=paper_id,
            user_id=user_id,
            task_type=task_type,
        )

        return task

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ProcessingTask:
        """Update task status and progress.

        Args:
            db: AsyncSession database connection
            task_id: Task ID
            status: New status (pending, processing, completed, failed)
            progress: Optional progress info dict
            error_message: Optional error message for failed status

        Returns:
            Updated ProcessingTask object

        Raises:
            ValueError: If task not found
        """
        # Get task
        query = select(ProcessingTask).where(ProcessingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError("Task not found")

        # Update fields
        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if error_message:
            task.error_message = error_message

        if status == "completed":
            task.completed_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info(
            "Task status updated",
            task_id=task_id,
            status=status,
            progress=progress,
        )

        return task

    @staticmethod
    async def retry_task(
        db: AsyncSession,
        task_id: str,
        user_id: str,
    ) -> ProcessingTask:
        """Reset task for retry.

        Args:
            db: AsyncSession database connection
            task_id: Task ID
            user_id: User ID (for ownership verification)

        Returns:
            Updated ProcessingTask object

        Raises:
            ValueError: If task not found or not owned by user
        """
        # Get task with ownership check
        task = await TaskService.get_task(db, task_id, user_id)

        # Reset for retry
        task.status = "pending"
        task.attempts = (task.attempts or 0) + 1
        task.error_message = None
        task.updated_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info(
            "Task reset for retry",
            task_id=task_id,
            user_id=user_id,
            attempts=task.attempts,
        )

        return task

    @staticmethod
    async def cancel_task(
        db: AsyncSession,
        task_id: str,
        user_id: str,
    ) -> bool:
        """Cancel a pending task.

        Args:
            db: AsyncSession database connection
            task_id: Task ID
            user_id: User ID (for ownership verification)

        Returns:
            True if cancelled successfully

        Raises:
            ValueError: If task not found, not owned, or not in pending status
        """
        # Get task with ownership check
        task = await TaskService.get_task(db, task_id, user_id)

        # Can only cancel pending tasks
        if task.status != "pending":
            raise ValueError(f"Cannot cancel task in status: {task.status}")

        # Delete task
        await db.delete(task)

        logger.info(
            "Task cancelled",
            task_id=task_id,
            user_id=user_id,
        )

        return True

    @staticmethod
    def get_progress_stages() -> Dict[str, Dict[str, Any]]:
        """Get PDF processing progress stage definitions.

        Returns:
            Dictionary of stage definitions:
                {
                    "upload": {"name", "label", "start", "end", "description"},
                    "parsing": {...},
                    "indexing": {...},
                    "multimodal": {...}
                }
        """
        return PROGRESS_STAGES.copy()

    @staticmethod
    def calculate_progress(
        current_stage: str,
        stage_progress: float = 0.0,
    ) -> int:
        """Calculate overall progress percentage.

        Args:
            current_stage: Current stage name
            stage_progress: Progress within current stage (0.0 to 1.0)

        Returns:
            Overall progress percentage (0 to 100)
        """
        stages = TaskService.get_progress_stages()

        if current_stage not in stages:
            return 0

        stage = stages[current_stage]
        stage_range = stage["end"] - stage["start"]
        overall = stage["start"] + (stage_range * stage_progress)

        return min(100, max(0, int(overall)))


__all__ = ["TaskService"]