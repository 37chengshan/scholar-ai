"""Reading Progress API endpoints.

Provides endpoints for tracking user's reading progress on papers:
- GET /api/v1/reading-progress - Get progress for all papers
- GET /api/v1/reading-progress/:paperId - Get paper progress
- POST /api/v1/reading-progress/:paperId - Update progress
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.reading_progress import ReadingProgress
from app.models.paper import Paper
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ProgressCreate(BaseModel):
    """Request to create/update reading progress."""
    currentPage: int = Field(..., ge=1)
    totalPages: Optional[int] = Field(None, ge=1)


class ProgressResponse(BaseModel):
    """Response for reading progress."""
    id: str
    paper_id: str
    user_id: str
    current_page: int
    total_pages: Optional[int]
    last_read_at: str

    class Config:
        from_attributes = True


class ProgressWithPaperResponse(BaseModel):
    """Response for reading progress with paper details."""
    id: str
    paper_id: str
    user_id: str
    current_page: int
    total_pages: Optional[int]
    last_read_at: str
    # Paper details
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    page_count: Optional[int] = None
    progress: Optional[int] = None


class ProgressListResponse(BaseModel):
    """Response for progress list."""
    success: bool = True
    data: List[ProgressWithPaperResponse]


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get("", response_model=ProgressListResponse)
async def list_reading_progress(
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Get all reading progress for user with paper details."""
    try:
        # Get all reading progress for user with paper details
        result = await db.execute(
            select(ReadingProgress)
            .options(selectinload(ReadingProgress.paper))
            .where(ReadingProgress.user_id == user_id)
            .order_by(desc(ReadingProgress.last_read_at))
        )
        progress_list = result.scalars().all()

        data = []
        for rp in progress_list:
            paper = rp.paper
            progress = None
            if paper and paper.page_count and rp.current_page:
                progress = min(100, round((rp.current_page / paper.page_count) * 100))

            data.append(ProgressWithPaperResponse(
                id=rp.id,
                paper_id=rp.paper_id,
                user_id=rp.user_id,
                current_page=rp.current_page,
                total_pages=rp.total_pages,
                last_read_at=rp.last_read_at.isoformat(),
                title=paper.title if paper else None,
                authors=paper.authors if paper else None,
                page_count=paper.page_count if paper else None,
                progress=progress
            ))

        return ProgressListResponse(success=True, data=data)

    except Exception as e:
        logger.error("Failed to list reading progress", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list progress: {str(e)}")
        )


@router.get("/{paper_id}")
async def get_paper_progress(
    paper_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Get reading progress for a specific paper."""
    try:
        # Verify paper exists and belongs to user
        paper_result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found")
            )

        # Get reading progress
        result = await db.execute(
            select(ReadingProgress).where(
                ReadingProgress.paper_id == paper_id,
                ReadingProgress.user_id == user_id
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            # Return default progress if not exists
            return {
                "success": True,
                "data": {
                    "paper_id": paper_id,
                    "user_id": user_id,
                    "current_page": 1,
                    "total_pages": paper.page_count,
                    "last_read_at": None
                }
            }

        return {
            "success": True,
            "data": {
                "id": progress.id,
                "paper_id": progress.paper_id,
                "user_id": progress.user_id,
                "current_page": progress.current_page,
                "total_pages": progress.total_pages,
                "last_read_at": progress.last_read_at.isoformat() if progress.last_read_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get paper progress", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get progress: {str(e)}")
        )


@router.post("/{paper_id}")
async def upsert_paper_progress(
    paper_id: str,
    request: ProgressCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Create or update reading progress for a paper."""
    try:
        # Verify paper exists and belongs to user
        paper_result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found")
            )

        # Check if progress exists
        result = await db.execute(
            select(ReadingProgress).where(
                ReadingProgress.paper_id == paper_id,
                ReadingProgress.user_id == user_id
            )
        )
        progress = result.scalar_one_or_none()

        total_pages = request.totalPages or paper.page_count

        if progress:
            # Update existing
            progress.current_page = request.currentPage
            progress.total_pages = total_pages
            # last_read_at is auto-updated by database
        else:
            # Create new
            progress = ReadingProgress(
                paper_id=paper_id,
                user_id=user_id,
                current_page=request.currentPage,
                total_pages=total_pages
            )
            db.add(progress)

        await db.flush()
        await db.refresh(progress)

        logger.info(
            "Reading progress updated",
            paper_id=paper_id,
            page=request.currentPage,
            user_id=user_id
        )

        return {
            "success": True,
            "data": {
                "id": progress.id,
                "paper_id": progress.paper_id,
                "user_id": progress.user_id,
                "current_page": progress.current_page,
                "total_pages": progress.total_pages,
                "last_read_at": progress.last_read_at.isoformat() if progress.last_read_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update progress", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update progress: {str(e)}")
        )