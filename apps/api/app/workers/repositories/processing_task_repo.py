"""Repository for ProcessingTask updates in worker context."""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import ProcessingTask


class ProcessingTaskWorkerRepository:
    """Facade for processing task CRUD used by Celery workers."""

    async def get_by_id(self, task_id: str, db: AsyncSession) -> ProcessingTask | None:
        result = await db.execute(select(ProcessingTask).where(ProcessingTask.id == task_id))
        return result.scalar_one_or_none()

    async def get_by_paper_id(
        self,
        paper_id: str,
        db: AsyncSession,
    ) -> ProcessingTask | None:
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.paper_id == paper_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        task_id: str,
        paper_id: str,
        storage_key: str,
        db: AsyncSession,
    ) -> ProcessingTask:
        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="processing",
            storage_key=storage_key,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    async def set_status(
        self,
        task_id: str,
        status: str,
        db: AsyncSession,
        completed: bool = False,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status}
        if completed:
            values["completed_at"] = datetime.now(timezone.utc)
        if error_message is not None:
            values["error_message"] = error_message
        await db.execute(update(ProcessingTask).where(ProcessingTask.id == task_id).values(**values))
        await db.commit()

    async def set_failed_by_paper_id(
        self,
        paper_id: str,
        error_message: str,
        db: AsyncSession,
    ) -> None:
        await db.execute(
            update(ProcessingTask)
            .where(ProcessingTask.paper_id == paper_id)
            .values(status="failed", error_message=error_message)
        )
        await db.commit()
