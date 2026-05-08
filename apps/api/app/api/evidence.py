from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.services.evidence_source_service import resolve_evidence_source

router = APIRouter()


@router.get("/source/{source_chunk_id}")
async def get_evidence_source(
    source_chunk_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    item = await resolve_evidence_source(
        db,
        source_chunk_id=source_chunk_id,
        user_id=user_id,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source chunk not found",
        )

    return item
