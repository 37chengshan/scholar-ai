"""Processing task repository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import ProcessingTask


class TaskRepository:
    """Repository for processing task data access."""

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: str) -> Optional[ProcessingTask]:
        result = await db.execute(select(ProcessingTask).where(ProcessingTask.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_paper_id(db: AsyncSession, paper_id: str) -> Optional[ProcessingTask]:
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.paper_id == paper_id)
        )
        return result.scalar_one_or_none()
