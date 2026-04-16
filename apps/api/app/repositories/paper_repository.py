"""Paper repository.

Encapsulates DB reads/writes used by paper service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Paper, PaperChunk, ReadingProgress


class PaperRepository:
    """Persistence operations for papers."""

    @staticmethod
    async def list_papers(
        db: AsyncSession,
        user_id: str,
        *,
        page: int,
        limit: int,
        starred: Optional[bool] = None,
        read_status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Paper], int]:
        query = select(Paper).where(Paper.user_id == user_id)

        if starred is not None:
            query = query.where(Paper.starred == starred)

        if date_from:
            query = query.where(Paper.created_at >= date_from)

        if date_to:
            query = query.where(Paper.created_at <= date_to)

        if read_status == "in-progress":
            query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
            query = query.where(ReadingProgress.user_id == user_id)
            query = query.where(ReadingProgress.current_page > 0)
            query = query.where(
                ReadingProgress.current_page < func.coalesce(ReadingProgress.total_pages, 999999)
            )
        elif read_status == "completed":
            query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
            query = query.where(ReadingProgress.user_id == user_id)
            query = query.where(
                ReadingProgress.current_page >= func.coalesce(ReadingProgress.total_pages, 0)
            )
        elif read_status == "unread":
            progress_subquery = (
                select(ReadingProgress.paper_id)
                .where(ReadingProgress.user_id == user_id)
                .distinct()
            )
            query = query.where(Paper.id.not_in(progress_subquery))

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * limit
        query = query.order_by(Paper.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def search_papers(
        db: AsyncSession,
        user_id: str,
        *,
        query_text: str,
        page: int,
        limit: int,
    ) -> Tuple[List[Paper], int]:
        search_term = f"%{query_text.lower()}%"
        escaped_q = query_text.replace("'", "''")

        base_query = (
            select(Paper)
            .where(Paper.user_id == user_id)
            .where(
                or_(
                    func.lower(Paper.title).ilike(search_term),
                    func.lower(Paper.abstract).ilike(search_term),
                    text(
                        f"EXISTS (SELECT 1 FROM unnest(papers.authors) a WHERE LOWER(a) LIKE LOWER('{escaped_q}%'))"
                    ),
                )
            )
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * limit
        paged_query = base_query.order_by(Paper.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(paged_query)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_user_paper(db: AsyncSession, user_id: str, paper_id: str) -> Optional[Paper]:
        result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_paper_by_title(
        db: AsyncSession, user_id: str, title: str
    ) -> Optional[Paper]:
        result = await db.execute(
            select(Paper).where(Paper.user_id == user_id, Paper.title == title)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_chunks(db: AsyncSession, paper_id: str) -> List[PaperChunk]:
        result = await db.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.page_start, PaperChunk.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_user_papers_by_ids(
        db: AsyncSession, user_id: str, paper_ids: List[str]
    ) -> List[Paper]:
        result = await db.execute(
            select(Paper).where(Paper.user_id == user_id, Paper.id.in_(paper_ids))
        )
        return list(result.scalars().all())
