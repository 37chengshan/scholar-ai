"""KB ReviewDraft and Run APIs (Phase 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.schemas.review_draft import (
    ReviewClaimRepairRequest,
    ReviewDraftCreateRequest,
    ReviewDraftRetryRequest,
)
from app.services.review_draft_service import ReviewDraftService


router = APIRouter()


@router.post("/{kb_id}/review-drafts")
async def create_review_draft(
    kb_id: str,
    request: ReviewDraftCreateRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    draft = await service.create_or_regenerate(
        kb_id=kb_id,
        user_id=user_id,
        mode=request.mode,
        paper_ids=request.paper_ids,
        question=request.question,
        target_review_draft_id=request.target_review_draft_id,
    )
    return {
        "success": True,
        "data": service.to_review_dto(draft).model_dump(mode="json"),
    }


@router.get("/{kb_id}/review-drafts")
async def list_review_drafts(
    kb_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    rows, total = await service.list_drafts(
        kb_id=kb_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": {
            "items": [service.to_review_dto(row).model_dump(mode="json") for row in rows],
        },
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
        },
    }


@router.get("/{kb_id}/review-drafts/{draft_id}")
async def get_review_draft(
    kb_id: str,
    draft_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    draft = await service.get_draft(kb_id=kb_id, draft_id=draft_id, user_id=user_id)
    return {
        "success": True,
        "data": service.to_review_dto(draft).model_dump(mode="json"),
    }


@router.post("/{kb_id}/review-drafts/{draft_id}/retry")
async def retry_review_draft(
    kb_id: str,
    draft_id: str,
    request: ReviewDraftRetryRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    if request.force:
        # Reserved behavior hook; current retry flow is idempotent and force-safe.
        pass
    draft = await service.retry_draft(kb_id=kb_id, draft_id=draft_id, user_id=user_id)
    return {
        "success": True,
        "data": service.to_review_dto(draft).model_dump(mode="json"),
    }


@router.post("/{kb_id}/review-drafts/{draft_id}/claims/repair")
async def repair_review_claim(
    kb_id: str,
    draft_id: str,
    request: ReviewClaimRepairRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    draft = await service.repair_claim(
        kb_id=kb_id,
        draft_id=draft_id,
        paragraph_id=request.paragraph_id,
        claim_id=request.claim_id,
        user_id=user_id,
    )
    return {
        "success": True,
        "data": service.to_review_dto(draft).model_dump(mode="json"),
    }


@router.get("/{kb_id}/runs")
async def list_kb_runs(
    kb_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    service = ReviewDraftService(db)
    rows, total = await service.list_runs(
        kb_id=kb_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": {
            "items": [service.to_run_summary(row) for row in rows],
        },
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": total,
        },
    }
