"""Paper CRUD operations - list, search, get, update, delete.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- GET /api/v1/papers - List papers with filters
- GET /api/v1/papers/search - Search papers
- POST /api/v1/papers - Create paper (get upload URL)
- GET /api/v1/papers/{id} - Get paper details
- PATCH /api/v1/papers/{id} - Update paper
- DELETE /api/v1/papers/{id} - Delete paper
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, text

from app.database import get_db
from app.deps import get_current_user
from app.models import Paper, ProcessingTask, PaperChunk, UploadHistory, ReadingProgress
from app.services.auth_service import User
from app.utils.problem_detail import ErrorTypes
from app.config import settings

from .paper_shared import (
    PaperListResponse,
    PaperCreateRequest,
    PaperCreateResponse,
    create_error_response,
    format_paper_response,
    datetime,
    timezone,
    uuid4,
    logger,
)


router = APIRouter()


class PaperUpdateRequest(BaseModel):
    """Request to update paper metadata."""

    title: Optional[str] = None
    authors: Optional[list] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[list] = None
    starred: Optional[bool] = None
    projectId: Optional[str] = None
    readingNotes: Optional[str] = None


@router.get("/", response_model=PaperListResponse)
async def list_papers(
    request: Request,
    page: int = 1,
    limit: int = 20,
    starred: Optional[str] = None,
    readStatus: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """List papers with pagination and filters."""
    instance = str(request.url.path)
    user_id = current_user.id

    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit

    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.user_id == user_id)
    )

    if starred is not None:
        if starred.lower() == "true":
            query = query.where(Paper.starred == True)
        elif starred.lower() == "false":
            query = query.where(Paper.starred == False)

    if dateFrom:
        try:
            date_from_dt = datetime.fromisoformat(dateFrom)
            query = query.where(Paper.created_at >= date_from_dt)
        except ValueError:
            pass

    if dateTo:
        try:
            date_to_dt = datetime.fromisoformat(dateTo)
            query = query.where(Paper.created_at <= date_to_dt)
        except ValueError:
            pass

    if readStatus == "in-progress":
        query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        query = query.where(ReadingProgress.user_id == user_id)
        query = query.where(ReadingProgress.current_page > 0)
        query = query.where(
            ReadingProgress.current_page
            < func.coalesce(ReadingProgress.total_pages, 999999)
        )
    elif readStatus == "completed":
        query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        query = query.where(ReadingProgress.user_id == user_id)
        query = query.where(
            ReadingProgress.current_page
            >= func.coalesce(ReadingProgress.total_pages, 0)
        )
    elif readStatus == "unread":
        progress_subquery = (
            select(ReadingProgress.paper_id)
            .where(ReadingProgress.user_id == user_id)
            .distinct()
        )
        query = query.where(Paper.id.not_in(progress_subquery))

    query = query.order_by(Paper.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    formatted_papers = []
    for paper, task in rows:
        paper_dict = format_paper_response(paper, task)
        formatted_papers.append(paper_dict)

    count_query = select(func.count(Paper.id)).where(Paper.user_id == user_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit

    return PaperListResponse(
        success=True,
        data={
            "papers": formatted_papers,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
        },
    )


@router.get("/search", response_model=PaperListResponse)
async def search_papers(
    request: Request,
    q: str,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Search papers by title, authors, or abstract."""
    instance = str(request.url.path)
    user_id = current_user.id

    if not q or len(q) < 1 or len(q) > 100:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Search query must be between 1 and 100 characters",
            instance=instance,
        )

    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit

    search_term = f"%{q.lower()}%"
    escaped_q = q.replace("'", "''")

    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
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
        .order_by(Paper.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    formatted_papers = [format_paper_response(p, t) for p, t in rows]

    count_query = (
        select(func.count(Paper.id))
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
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit

    return PaperListResponse(
        success=True,
        data={
            "papers": formatted_papers,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
            "query": q,
        },
    )


@router.post(
    "/", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_paper(
    request: Request,
    body: PaperCreateRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Request upload URL for a new paper."""
    instance = str(request.url.path)
    user_id = current_user.id

    filename = body.filename

    if not filename:
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Filename is required",
            instance=instance,
        )

    if not filename.lower().endswith(".pdf"):
        raise create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only PDF files are accepted",
            instance=instance,
        )

    title = filename.replace(".pdf", "").replace(".PDF", "")

    existing_query = select(Paper).where(
        Paper.user_id == user_id,
        Paper.title == title,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists',
            instance=instance,
        )

    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid4()}.pdf"
    paper_id = str(uuid4())
    now = datetime.now(timezone.utc)

    paper = Paper(
        id=paper_id,
        title=title,
        authors=[],
        status="pending",
        user_id=user_id,
        storage_key=storage_key,
        keywords=[],
        created_at=now,
        updated_at=now,
    )
    db.add(paper)

    upload_history_id = str(uuid4())
    upload_history = UploadHistory(
        id=upload_history_id,
        user_id=user_id,
        filename=filename,
        status="PROCESSING",
        created_at=now,
        updated_at=now,
    )
    db.add(upload_history)

    use_local_storage = settings.USE_LOCAL_STORAGE
    upload_url = f"/api/v1/papers/upload/local/{storage_key}"

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": paper_id,
            "uploadUrl": upload_url,
            "storageKey": storage_key,
            "expiresIn": 3600,
        },
    )


@router.get("/{paper_id}")
async def get_paper(
    request: Request,
    paper_id: str,
    includeChunks: Optional[bool] = False,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get paper details."""
    instance = str(request.url.path)
    user_id = current_user.id

    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.id == paper_id)
        .where(Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper, task = row
    paper_dict = format_paper_response(paper, task)

    if includeChunks:
        chunks_query = (
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.page_start, PaperChunk.id)
        )
        chunks_result = await db.execute(chunks_query)
        chunks = chunks_result.scalars().all()

        paper_dict["chunks"] = [
            {
                "id": c.id,
                "content": c.content,
                "section": c.section,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "is_table": c.is_table,
                "is_figure": c.is_figure,
            }
            for c in chunks
        ]

    return {"success": True, "data": paper_dict}


@router.patch("/{paper_id}")
async def update_paper(
    request: Request,
    paper_id: str,
    body: PaperUpdateRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update paper metadata."""
    instance = str(request.url.path)
    user_id = current_user.id

    existing_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    existing_result = await db.execute(existing_query)
    paper = existing_result.scalar_one_or_none()

    if not paper:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    if body.title is not None:
        paper.title = body.title
    if body.authors is not None:
        paper.authors = body.authors
    if body.year is not None:
        paper.year = body.year
    if body.abstract is not None:
        paper.abstract = body.abstract
    if body.keywords is not None:
        paper.keywords = body.keywords
    if body.starred is not None:
        paper.starred = body.starred
    if body.projectId is not None:
        paper.project_id = body.projectId
    if body.readingNotes is not None:
        paper.reading_notes = body.readingNotes

    paper.updated_at = datetime.now(timezone.utc)
    await db.refresh(paper)

    return {"success": True, "data": format_paper_response(paper)}


@router.delete("/{paper_id}")
async def delete_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a paper."""
    instance = str(request.url.path)
    user_id = current_user.id

    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    storage_key = paper.storage_key
    if storage_key:
        file_path = f"{settings.LOCAL_STORAGE_PATH}/{storage_key}"
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.delete(paper)

    return {"success": True, "data": {"message": "Paper deleted successfully"}}


__all__ = ["router"]
