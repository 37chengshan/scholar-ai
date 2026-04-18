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

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.database import get_db
from app.deps import get_current_user
from app.services.auth_service import User
from app.services.paper_service import PaperService
from app.utils.problem_detail import ErrorTypes

from .paper_shared import (
    PaperListResponse,
    PaperCreateRequest,
    PaperCreateResponse,
    PaperResponse,
    PaperData,
    ChunkData,
    BatchDeleteResponse,
    BatchDeleteData,
    BatchStarResponse,
    BatchStarData,
    MessageResponse,
    MessageData,
    create_error_response,
    format_paper_response,
    datetime,
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
    user_id = current_user.id

    page = max(1, page)
    limit = min(100, max(1, limit))

    starred_bool: Optional[bool] = None
    if starred is not None:
        if starred.lower() == "true":
            starred_bool = True
        elif starred.lower() == "false":
            starred_bool = False

    date_from_dt = None
    if dateFrom:
        try:
            date_from_dt = datetime.fromisoformat(dateFrom)
        except ValueError:
            pass

    date_to_dt = None
    if dateTo:
        try:
            date_to_dt = datetime.fromisoformat(dateTo)
        except ValueError:
            pass

    result = await PaperService.list_papers_for_api(
        db,
        user_id,
        page=page,
        limit=limit,
        starred=starred_bool,
        read_status=readStatus,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )

    formatted_papers = []
    for paper in result["papers"]:
        paper_dict = format_paper_response(paper, result["task_map"].get(paper.id))
        formatted_papers.append(paper_dict)

    return PaperListResponse(
        success=True,
        data={
            "papers": formatted_papers,
            "items": formatted_papers,
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "totalPages": result["total_pages"],
            "meta": {
                "limit": result["limit"],
                "offset": (result["page"] - 1) * result["limit"],
                "total": result["total"],
            },
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
    result = await PaperService.search_papers_for_api(
        db,
        user_id,
        query_text=q,
        page=page,
        limit=limit,
    )

    formatted_papers = [
        format_paper_response(p, result["task_map"].get(p.id)) for p in result["papers"]
    ]

    return PaperListResponse(
        success=True,
        data={
            "papers": formatted_papers,
            "items": formatted_papers,
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "totalPages": result["total_pages"],
            "meta": {
                "limit": result["limit"],
                "offset": (result["page"] - 1) * result["limit"],
                "total": result["total"],
            },
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

    try:
        create_data = await PaperService.create_paper_for_api(
            db,
            user_id,
            filename=filename,
        )
    except ValueError as exc:
        title = str(exc).replace("Duplicate paper title: ", "")
        raise create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists',
            instance=instance,
        )

    return PaperCreateResponse(
        success=True,
        data=create_data,
    )


@router.get("/{paper_id}", response_model=PaperResponse)
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

    try:
        result = await PaperService.get_paper_for_api(
            db,
            user_id,
            paper_id=paper_id,
            include_chunks=bool(includeChunks),
        )
    except ValueError:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper_dict = format_paper_response(result["paper"], result["task"])

    if includeChunks:
        paper_dict["chunks"] = [
            ChunkData(
                id=c.id,
                content=c.content,
                section=c.section,
                page_start=c.page_start,
                page_end=c.page_end,
                is_table=c.is_table,
                is_figure=c.is_figure,
            )
            for c in result["chunks"]
        ]

    return PaperResponse(success=True, data=PaperData(**paper_dict))


@router.patch("/{paper_id}", response_model=PaperResponse)
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

    try:
        paper = await PaperService.update_paper_for_api(
            db,
            user_id,
            paper_id=paper_id,
            updates=body.model_dump(exclude_unset=True),
        )
    except ValueError:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    return PaperResponse(success=True, data=PaperData(**format_paper_response(paper)))


@router.delete("/{paper_id}", response_model=MessageResponse)
async def delete_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a paper."""
    instance = str(request.url.path)
    user_id = current_user.id

    try:
        await PaperService.delete_paper_for_api(
            db,
            user_id,
            paper_id=paper_id,
        )
    except ValueError:
        raise create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    return MessageResponse(success=True, data=MessageData(message="Paper deleted successfully"))


class BatchDeleteRequest(BaseModel):
    """Request to delete multiple papers."""
    paper_ids: list[str] = Field(..., min_length=1, max_length=100)


class BatchStarRequest(BaseModel):
    """Request to star/unstar multiple papers."""
    paper_ids: list[str] = Field(..., min_length=1, max_length=100)
    starred: bool = Field(..., description="True to star, False to unstar")


@router.post("/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_papers(
    body: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete multiple papers in a single request."""
    user_id = current_user.id

    paper_ids = body.paper_ids
    requested_count = len(paper_ids)

    deleted_count = await PaperService.batch_delete_for_api(
        db,
        user_id,
        paper_ids=paper_ids,
    )

    return BatchDeleteResponse(
        success=True,
        data=BatchDeleteData(
            deletedCount=deleted_count,
            requestedCount=requested_count,
            failedIds=[],  # Service returns count only; per-item errors tracked in future
            message=f"Successfully deleted {deleted_count} of {requested_count} papers",
        ),
    )


@router.post("/batch/star", response_model=BatchStarResponse)
async def batch_star_papers(
    request: Request,
    body: BatchStarRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Star or unstar multiple papers in a single request."""
    user_id = current_user.id

    paper_ids = body.paper_ids
    starred = body.starred
    requested_count = len(paper_ids)

    updated_count = await PaperService.batch_star_for_api(
        db,
        user_id,
        paper_ids=paper_ids,
        starred=starred,
    )

    return BatchStarResponse(
        success=True,
        data=BatchStarData(
            updatedCount=updated_count,
            requestedCount=requested_count,
            failedIds=[],  # Service returns count only; per-item errors tracked in future
            starred=starred,
            message=f"Successfully updated starred status for {updated_count} papers",
        ),
    )


__all__ = ["router"]
