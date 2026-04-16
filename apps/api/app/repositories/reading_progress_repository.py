"""Reading progress repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading_progress import ReadingProgress


class ReadingProgressRepository:
    """Minimal repository for reading progress persistence."""

    @staticmethod
    async def get_for_user_paper(
        db: AsyncSession, user_id: str, paper_id: str
    ) -> Optional[ReadingProgress]:
        result = await db.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.paper_id == paper_id,
            )
        )
        return result.scalar_one_or_none()
