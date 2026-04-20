"""Session repository with common query helpers."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm_session import Session


class SessionRepository:
    """Repository for session data access."""

    @staticmethod
    async def get_by_id_and_user(
        db: AsyncSession,
        session_id: str,
        user_id: str,
    ) -> Optional[Session]:
        result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: str, limit: int = 50) -> List[Session]:
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
