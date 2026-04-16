"""Dashboard API endpoints.

Provides endpoints for dashboard statistics:
- GET /api/v1/dashboard/stats - Get dashboard statistics
- GET /api/v1/dashboard/trends - Get time-series data
- GET /api/v1/dashboard/recent-papers - Get recently accessed papers
- GET /api/v1/dashboard/reading-stats - Get reading statistics
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.models.reading_progress import ReadingProgress
from app.models.query import Query as QueryModel
from app.models.orm_session import Session
from app.models.token_usage_log import TokenUsageLog
from app.utils.logger import logger
from app.middleware.auth import get_current_user
from app.services.auth_service import User
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    totalPapers: int
    starredPapers: int
    processingPapers: int
    completedPapers: int
    queriesCount: int
    sessionsCount: int
    projectsCount: int
    llmTokens: int


class DashboardStatsResponse(BaseModel):
    """Response for dashboard stats."""
    success: bool = True
    data: DashboardStats


class DataPoint(BaseModel):
    """Single data point for trends."""
    date: str
    papers: int
    queries: int


class DashboardTrendsResponse(BaseModel):
    """Response for dashboard trends."""
    success: bool = True
    data: Dict[str, Any]


class RecentPaper(BaseModel):
    """Recent paper with progress."""
    id: str
    title: str
    authors: Optional[List[str]]
    year: Optional[int]
    starred: Optional[bool]
    status: Optional[str]
    pageCount: Optional[int]
    currentPage: int
    lastReadAt: Optional[str]
    progress: Optional[int]


class RecentPapersResponse(BaseModel):
    """Response for recent papers."""
    success: bool = True
    data: List[RecentPaper]


class ReadingStats(BaseModel):
    """Reading statistics."""
    totalPapersWithProgress: int
    totalPagesRead: int
    completedPapers: int
    averageProgress: int


class ReadingStatsResponse(BaseModel):
    """Response for reading stats."""
    success: bool = True
    data: ReadingStats


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics.

    Returns counts for papers, queries, sessions, projects, and LLM tokens.
    """
    user_id = str(current_user.id)
    try:
        # Run all aggregations
        total_papers_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.user_id == user_id)
        )
        total_papers = total_papers_result.scalar() or 0

        starred_papers_result = await db.execute(
            select(func.count(Paper.id)).where(
                Paper.user_id == user_id,
                Paper.starred == True
            )
        )
        starred_papers = starred_papers_result.scalar() or 0

        processing_papers_result = await db.execute(
            select(func.count(Paper.id)).where(
                Paper.user_id == user_id,
                Paper.status == "processing"
            )
        )
        processing_papers = processing_papers_result.scalar() or 0

        completed_papers_result = await db.execute(
            select(func.count(Paper.id)).where(
                Paper.user_id == user_id,
                Paper.status == "completed"
            )
        )
        completed_papers = completed_papers_result.scalar() or 0

        queries_result = await db.execute(
            select(func.count(QueryModel.id)).where(QueryModel.user_id == user_id)
        )
        queries_count = queries_result.scalar() or 0

        sessions_result = await db.execute(
            select(func.count(Session.id)).where(Session.user_id == user_id)
        )
        sessions_count = sessions_result.scalar() or 0

        projects_result = await db.execute(
            select(func.count(Project.id)).where(Project.user_id == user_id)
        )
        projects_count = projects_result.scalar() or 0

        # LLM tokens from token_usage_logs
        tokens_result = await db.execute(
            select(func.sum(TokenUsageLog.total_tokens)).where(TokenUsageLog.user_id == user_id)
        )
        llm_tokens = tokens_result.scalar() or 0

        return DashboardStatsResponse(
            success=True,
            data=DashboardStats(
                totalPapers=total_papers,
                starredPapers=starred_papers,
                processingPapers=processing_papers,
                completedPapers=completed_papers,
                queriesCount=queries_count,
                sessionsCount=sessions_count,
                projectsCount=projects_count,
                llmTokens=llm_tokens or 0
            )
        )

    except Exception as e:
        logger.error("Failed to get dashboard stats", error=str(e))
        raise


@router.get("/trends", response_model=DashboardTrendsResponse)
async def get_dashboard_trends(
    period: str = Query("weekly", pattern=r"^(weekly|monthly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get time-series data for dashboard.

    Returns papers and queries counts grouped by day.
    """
    user_id = str(current_user.id)
    try:
        days = 30 if period == "monthly" else 7
        since = datetime.now() - timedelta(days=days)

        # Get papers created in the time range
        papers_result = await db.execute(
            select(Paper.created_at).where(
                Paper.user_id == user_id,
                Paper.created_at >= since
            )
        )
        papers = papers_result.scalars().all()

        # Get queries in the time range
        queries_result = await db.execute(
            select(QueryModel.created_at).where(
                QueryModel.user_id == user_id,
                QueryModel.created_at >= since
            )
        )
        queries = queries_result.scalars().all()

        # Group by day
        data_points = []
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            day_start = datetime.strptime(date_str, "%Y-%m-%d")
            day_end = day_start + timedelta(days=1)

            papers_count = sum(
                1 for p in papers if p and day_start <= p.replace(tzinfo=None) < day_end
            )
            queries_count = sum(
                1 for q in queries if q and day_start <= q.replace(tzinfo=None) < day_end
            )

            data_points.append(DataPoint(
                date=date_str,
                papers=papers_count,
                queries=queries_count
            ))

        return DashboardTrendsResponse(
            success=True,
            data={
                "dataPoints": [dp.model_dump() for dp in data_points],
                "period": period
            }
        )

    except Exception as e:
        logger.error("Failed to get dashboard trends", error=str(e))
        raise


@router.get("/recent-papers", response_model=RecentPapersResponse)
async def get_recent_papers(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recently accessed papers.

    Returns papers sorted by last read time with progress info.
    """
    user_id = str(current_user.id)
    try:
        # Get recent papers by reading progress
        result = await db.execute(
            select(ReadingProgress)
            .where(ReadingProgress.user_id == user_id)
            .order_by(ReadingProgress.last_read_at.desc())
            .limit(limit)
        )
        progress_list = result.scalars().all()

        recent_papers = []
        for rp in progress_list:
            # Get paper details
            paper_result = await db.execute(
                select(Paper).where(Paper.id == rp.paper_id)
            )
            paper = paper_result.scalar_one_or_none()

            if paper:
                progress = None
                if paper.page_count and rp.current_page:
                    progress = min(100, round((rp.current_page / paper.page_count) * 100))

                recent_papers.append(RecentPaper(
                    id=paper.id,
                    title=paper.title or "Untitled",
                    authors=paper.authors,
                    year=paper.year,
                    starred=paper.starred,
                    status=paper.status,
                    pageCount=paper.page_count,
                    currentPage=rp.current_page,
                    lastReadAt=rp.last_read_at.isoformat() if rp.last_read_at else None,
                    progress=progress
                ))

        return RecentPapersResponse(success=True, data=recent_papers)

    except Exception as e:
        logger.error("Failed to get recent papers", error=str(e))
        raise


@router.get("/reading-stats", response_model=ReadingStatsResponse)
async def get_reading_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get reading statistics.

    Returns totals and averages for reading progress.
    """
    user_id = str(current_user.id)
    try:
        # Get all reading progress with paper page counts
        result = await db.execute(
            select(ReadingProgress, Paper.page_count)
            .join(Paper, ReadingProgress.paper_id == Paper.id)
            .where(ReadingProgress.user_id == user_id)
        )
        rows = result.all()

        total_papers_with_progress = len(rows)
        total_pages_read = sum(row[0].current_page for row in rows)

        # Count completed papers
        completed_papers = sum(
            1 for row in rows
            if row[1] and row[0].current_page >= row[1]
        )

        # Calculate average progress
        if rows:
            total_progress = sum(
                min(100, round((row[0].current_page / row[1]) * 100)) if row[1] else 0
                for row in rows
            )
            avg_progress = round(total_progress / len(rows))
        else:
            avg_progress = 0

        return ReadingStatsResponse(
            success=True,
            data=ReadingStats(
                totalPapersWithProgress=total_papers_with_progress,
                totalPagesRead=total_pages_read,
                completedPapers=completed_papers,
                averageProgress=avg_progress
            )
        )

    except Exception as e:
        logger.error("Failed to get reading stats", error=str(e))
        raise