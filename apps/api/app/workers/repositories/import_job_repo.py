"""Repository for ImportJob queries in worker context."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob


class ImportJobWorkerRepository:
    """Small query facade to avoid ad-hoc worker SQL snippets."""

    async def get_by_id(self, job_id: str, db: AsyncSession) -> ImportJob | None:
        result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_processing_task_id(
        self,
        processing_task_id: str,
        db: AsyncSession,
    ) -> ImportJob | None:
        result = await db.execute(
            select(ImportJob).where(ImportJob.processing_task_id == processing_task_id)
        )
        return result.scalar_one_or_none()
