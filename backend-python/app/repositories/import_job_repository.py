"""Import job repository placeholders.

Current phase adds repository boundary without changing import behavior.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob


class ImportJobRepository:
    """Minimal import job repository helper."""

    @staticmethod
    async def get_by_id(db: AsyncSession, import_job_id: str) -> Optional[ImportJob]:
        result = await db.execute(
            select(ImportJob).where(ImportJob.id == import_job_id)
        )
        return result.scalar_one_or_none()
