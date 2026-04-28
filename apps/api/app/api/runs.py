"""Run detail API (Phase 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.services.review_draft_service import ReviewDraftService


router = APIRouter()


@router.get("/{run_id}")
async def get_run_detail(
    run_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    run = await service.get_run(run_id=run_id, user_id=user_id)
    return {
        "success": True,
        "data": service.to_run_detail(run),
    }
