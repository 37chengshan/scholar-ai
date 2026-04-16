"""Knowledge base repository placeholders.

Current phase adds repository boundary without changing KB behavior.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase


class KnowledgeBaseRepository:
    """Minimal KB repository helper."""

    @staticmethod
    async def get_user_kb(db: AsyncSession, user_id: str, kb_id: str) -> Optional[KnowledgeBase]:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
