"""Paper management API routes.

Migrated from Node.js papers.ts - provides full CRUD operations for papers.
Migrated to SQLAlchemy ORM from raw asyncpg queries.

Endpoints:
- GET /api/v1/papers - List papers with pagination and filters
- POST /api/v1/papers - Request upload URL for new paper
- POST /api/v1/papers/webhook - Confirm upload completion
- POST /api/v1/papers/upload - Direct file upload
- GET /api/v1/papers/search - Search papers
- GET /api/v1/papers/:id - Get paper details
- GET /api/v1/papers/:id/status - Get processing status
- PATCH /api/v1/papers/:id - Update paper metadata
- DELETE /api/v1/papers/:id - Delete paper
- PATCH /api/v1/papers/:id/starred - Toggle starred status
- GET /api/v1/papers/:id/download - Download PDF file
- GET /api/v1/papers/:id/chunks - Get paper chunks
- POST /api/v1/papers/:id/regenerate-chunks - Regenerate chunks
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update, delete, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_current_user
from app.database import get_db
from app.models import Paper, ProcessingTask, PaperChunk, UploadHistory, ReadingProgress
from app.services.auth_service import User
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


router = APIRouter(tags=["Papers"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PaperListResponse(BaseModel):
    """Paper list response with pagination."""
    success: bool = True
    data: dict


class PaperCreateRequest(BaseModel):
    """Request to create a new paper (get upload URL)."""
    filename: str


class PaperCreateResponse(BaseModel):
    """Response for paper creation."""
    success: bool = True
    data: dict


class PaperUpdateRequest(BaseModel):
    """Request to update paper metadata."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    starred: Optional[bool] = None
    projectId: Optional[str] = None


class StarredRequest(BaseModel):
    """Request to toggle starred status."""
    starred: bool


class WebhookRequest(BaseModel):
    """Upload completion webhook request."""
    paperId: str
    storageKey: str


# =============================================================================
# Helper Functions
# =============================================================================

def _create_error_response(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    instance: str,
) -> HTTPException:
    """Create HTTPException with RFC 7807 ProblemDetail."""
    problem = ProblemDetail(
        type=error_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
    )
    return HTTPException(
        status_code=status_code,
        detail=problem.to_dict(),
    )


def _get_progress_percent(processing_status: str) -> int:
    """Calculate progress percentage based on processing status."""
    progress_map = {
        "pending": 0,
        "processing_ocr": 15,
        "parsing": 30,
        "extracting_imrad": 45,
        "generating_notes": 60,
        "storing_vectors": 75,
        "indexing_multimodal": 90,
        "completed": 100,
        "failed": 0,
    }
    return progress_map.get(processing_status, 0)


def _get_processing_stage(status: str) -> str:
    """Get human-readable processing stage name."""
    stage_names = {
        "processing_ocr": "OCR Processing",
        "parsing": "Parsing Document",
        "extracting_imrad": "Extracting Structure",
        "generating_notes": "Generating Notes",
        "storing_vectors": "Storing Vectors",
        "indexing_multimodal": "Indexing Multimodal",
        "completed": "Completed",
        "failed": "Failed",
        "pending": "Pending",
    }
    return stage_names.get(status, status)


def _format_paper_response(paper: Paper, task: Optional[ProcessingTask] = None) -> dict:
    """Format paper for API response."""
    paper_dict = {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "pdf_url": paper.pdf_url,
        "pdf_path": paper.pdf_path,
        "content": paper.content,
        "imrad_json": paper.imrad_json,
        "status": paper.status,
        "file_size": paper.file_size,
        "page_count": paper.page_count,
        "keywords": paper.keywords,
        "venue": paper.venue,
        "citations": paper.citations,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        "user_id": paper.user_id,
        "storage_key": paper.storage_key,
        "reading_notes": paper.reading_notes,
        "notes_version": paper.notes_version,
        "starred": paper.starred,
        "project_id": paper.project_id,
        "batch_id": paper.batch_id,
        "upload_progress": paper.upload_progress,
        "upload_status": paper.upload_status,
        "uploaded_at": paper.uploaded_at.isoformat() if paper.uploaded_at else None,
    }

    processing_status = task.status if task else paper.status or "pending"
    paper_dict["processingStatus"] = processing_status
    paper_dict["progress"] = _get_progress_percent(processing_status)
    paper_dict["processingError"] = task.error_message if task else None

    return paper_dict


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=PaperListResponse)
async def list_papers(
    request: Request,
    page: int = 1,
    limit: int = 20,
    starred: Optional[str] = None,
    readStatus: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List papers with pagination and filters.

    Query parameters:
        page: Page number (default 1)
        limit: Items per page (default 20, max 100)
        starred: Filter by starred status ('true' or 'false')
        readStatus: Filter by read status ('unread', 'in-progress', 'completed')
        dateFrom: Filter papers created after this date
        dateTo: Filter papers created before this date

    Returns:
        Paginated list of papers with processing status.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Validate pagination
    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit

    # Build base query with paper and processing task
    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.user_id == user_id)
    )

    # Apply filters
    if starred is not None:
        if starred.lower() == "true":
            query = query.where(Paper.starred == True)
        elif starred.lower() == "false":
            query = query.where(Paper.starred == False)

    # Date range filter
    if dateFrom:
        try:
            date_from_dt = datetime.fromisoformat(dateFrom)
            query = query.where(Paper.created_at >= date_from_dt)
        except ValueError:
            pass  # Invalid date format, ignore

    if dateTo:
        try:
            date_to_dt = datetime.fromisoformat(dateTo)
            query = query.where(Paper.created_at <= date_to_dt)
        except ValueError:
            pass  # Invalid date format, ignore

    # Handle readStatus filter with reading_progress join
    if readStatus == "in-progress":
        # Papers with reading_progress where current_page > 0 and < total_pages
        query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        query = query.where(ReadingProgress.user_id == user_id)
        query = query.where(ReadingProgress.current_page > 0)
        query = query.where(
            ReadingProgress.current_page < func.coalesce(ReadingProgress.total_pages, 999999)
        )
    elif readStatus == "completed":
        # Papers where current_page >= total_pages
        query = query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        query = query.where(ReadingProgress.user_id == user_id)
        query = query.where(
            ReadingProgress.current_page >= func.coalesce(ReadingProgress.total_pages, 0)
        )
    elif readStatus == "unread":
        # Papers without reading_progress for this user
        # Use a subquery to exclude papers with reading_progress
        progress_subquery = select(ReadingProgress.paper_id).where(
            ReadingProgress.user_id == user_id
        ).distinct()
        query = query.where(Paper.id.not_in(progress_subquery))

    # Order and paginate
    query = query.order_by(Paper.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Format papers
    formatted_papers = []
    for paper, task in rows:
        paper_dict = _format_paper_response(paper, task)
        formatted_papers.append(paper_dict)

    # Get total count
    count_query = select(func.count(Paper.id)).where(Paper.user_id == user_id)

    # Apply same filters for count
    if starred is not None:
        if starred.lower() == "true":
            count_query = count_query.where(Paper.starred == True)
        elif starred.lower() == "false":
            count_query = count_query.where(Paper.starred == False)

    if dateFrom:
        try:
            date_from_dt = datetime.fromisoformat(dateFrom)
            count_query = count_query.where(Paper.created_at >= date_from_dt)
        except ValueError:
            pass

    if dateTo:
        try:
            date_to_dt = datetime.fromisoformat(dateTo)
            count_query = count_query.where(Paper.created_at <= date_to_dt)
        except ValueError:
            pass

    if readStatus == "in-progress":
        count_query = count_query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        count_query = count_query.where(ReadingProgress.user_id == user_id)
        count_query = count_query.where(ReadingProgress.current_page > 0)
        count_query = count_query.where(
            ReadingProgress.current_page < func.coalesce(ReadingProgress.total_pages, 999999)
        )
    elif readStatus == "completed":
        count_query = count_query.join(ReadingProgress, Paper.id == ReadingProgress.paper_id)
        count_query = count_query.where(ReadingProgress.user_id == user_id)
        count_query = count_query.where(
            ReadingProgress.current_page >= func.coalesce(ReadingProgress.total_pages, 0)
        )
    elif readStatus == "unread":
        progress_subquery = select(ReadingProgress.paper_id).where(
            ReadingProgress.user_id == user_id
        ).distinct()
        count_query = count_query.where(Paper.id.not_in(progress_subquery))

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
    db: AsyncSession = Depends(get_db),
):
    """Search papers by title, authors, or abstract.

    Query parameters:
        q: Search query (required, 1-100 characters)
        page: Page number
        limit: Items per page

    Returns:
        Matching papers with pagination.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Validate query
    if not q or len(q) < 1 or len(q) > 100:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Search query must be between 1 and 100 characters",
            instance=instance,
        )

    # Validate pagination
    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit

    # Build search query (case-insensitive)
    search_term = f"%{q.lower()}%"

    # Search in title, abstract, and authors array
    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.user_id == user_id)
        .where(
            or_(
                func.lower(Paper.title).ilike(search_term),
                func.lower(Paper.abstract).ilike(search_term),
                # For array search, use raw SQL with unnest
                text(f"EXISTS (SELECT 1 FROM unnest(papers.authors) a WHERE LOWER(a) LIKE LOWER('{q.replace("'", "''")}%'))"),
            )
        )
        .order_by(Paper.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    # Format response
    formatted_papers = []
    for paper, task in rows:
        paper_dict = _format_paper_response(paper, task)
        formatted_papers.append(paper_dict)

    # Get total count
    count_query = (
        select(func.count(Paper.id))
        .where(Paper.user_id == user_id)
        .where(
            or_(
                func.lower(Paper.title).ilike(search_term),
                func.lower(Paper.abstract).ilike(search_term),
                text(f"EXISTS (SELECT 1 FROM unnest(papers.authors) a WHERE LOWER(a) LIKE LOWER('{q.replace("'", "''")}%'))"),
            )
        )
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_pages = (total + limit - 1) // limit

    logger.info(
        "Search completed",
        user_id=user_id,
        query=q,
        results=len(formatted_papers),
        total=total,
    )

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


@router.post("", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    request: Request,
    body: PaperCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request upload URL for a new paper.

    Creates a paper record and returns a presigned upload URL.
    Client must upload the file and then call /webhook to confirm.

    Request body:
        filename: Name of the PDF file

    Returns:
        Paper ID, upload URL, and storage key.
    """
    instance = str(request.url.path)
    user_id = current_user.id
    request_id = str(uuid4())

    filename = body.filename

    # Validate filename
    if not filename:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Filename is required",
            instance=instance,
        )

    # Check file extension
    if not filename.lower().endswith(".pdf"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only PDF files are accepted",
            instance=instance,
        )

    # Extract title from filename
    title = filename.replace(".pdf", "").replace(".PDF", "")

    # Check for duplicate
    existing_query = select(Paper).where(
        Paper.user_id == user_id,
        Paper.title == title,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise _create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists in your library.',
            instance=instance,
        )

    # Generate storage key
    import os
    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid4()}.pdf"

    # Create paper record
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

    # Create upload history record
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

    # Generate upload URL (for local storage, return local upload endpoint)
    use_local_storage = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"

    if use_local_storage:
        upload_url = f"/api/v1/papers/upload/local/{storage_key}"
    else:
        # For cloud storage, generate presigned URL (not implemented in this migration)
        upload_url = f"/api/v1/papers/upload/local/{storage_key}"

    logger.info(
        "Paper created, upload URL generated",
        user_id=user_id,
        paper_id=paper_id,
        filename=filename,
        request_id=request_id,
    )

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": paper_id,
            "uploadUrl": upload_url,
            "storageKey": storage_key,
            "expiresIn": 3600,
            "message": "Please upload file to the provided URL, then call /api/v1/papers/webhook to confirm",
        },
    )


@router.post("/webhook", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_webhook(
    request: Request,
    body: WebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm file upload and create processing task.

    Called after client has uploaded the file to storage.

    Request body:
        paperId: Paper ID from create response
        storageKey: Storage key from create response

    Returns:
        Task ID and processing status.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    paper_id = body.paperId
    storage_key = body.storageKey

    # Validate required fields
    if not paper_id or not storage_key:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="paperId and storageKey are required",
            instance=instance,
        )

    # Verify paper exists and belongs to user
    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Check if task already exists
    existing_task_query = select(ProcessingTask).where(
        ProcessingTask.paper_id == paper_id,
    )
    existing_task_result = await db.execute(existing_task_query)
    existing_task = existing_task_result.scalar_one_or_none()

    if existing_task:
        raise _create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Conflict",
            detail="Processing task already exists for this paper",
            instance=instance,
        )

    # Create processing task
    task_id = str(uuid4())
    now = datetime.now(timezone.utc)

    task = ProcessingTask(
        id=task_id,
        paper_id=paper_id,
        status="pending",
        storage_key=storage_key,
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    # Update paper status
    paper.status = "processing"
    paper.upload_status = "completed"
    paper.upload_progress = 100
    paper.uploaded_at = now
    paper.updated_at = now

    logger.info(
        "Processing task created",
        user_id=user_id,
        paper_id=paper_id,
        task_id=task_id,
    )

    return PaperCreateResponse(
        success=True,
        data={
            "taskId": task_id,
            "paperId": paper_id,
            "status": "pending",
            "progress": 0,
            "message": "Upload confirmed. Processing task created.",
        },
    )


@router.post("/upload", response_model=PaperCreateResponse, status_code=status.HTTP_201_CREATED)
async def direct_upload(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Direct file upload endpoint (for development and E2E tests).

    Uploads a PDF file directly and creates the paper record.

    Form data:
        file: PDF file

    Returns:
        Paper ID and task ID.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Validate file
    if not file:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="No file uploaded. Use form field name 'file'",
            instance=instance,
        )

    filename = file.filename or "untitled.pdf"

    # Check file extension
    if not filename.lower().endswith(".pdf"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Only PDF files are accepted",
            instance=instance,
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise _create_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_type=ErrorTypes.FILE_TOO_LARGE,
            title="File Too Large",
            detail="File size exceeds 50MB limit",
            instance=instance,
        )

    # Validate PDF magic bytes
    if not content.startswith(b"%PDF-"):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.INVALID_FILE_FORMAT,
            title="Invalid File Format",
            detail="File is not a valid PDF",
            instance=instance,
        )

    # Extract title
    title = filename.replace(".pdf", "").replace(".PDF", "")

    # Check for duplicates
    existing_query = select(Paper).where(
        Paper.user_id == user_id,
        Paper.title == title,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise _create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_type=ErrorTypes.CONFLICT,
            title="Duplicate Paper",
            detail=f'A paper with title "{title}" already exists',
            instance=instance,
        )

    # Generate storage key and save file
    import os
    import aiofiles
    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid4()}.pdf"
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create paper record
    paper_id = str(uuid4())
    now = datetime.now(timezone.utc)

    paper = Paper(
        id=paper_id,
        title=title,
        authors=[],
        status="processing",
        user_id=user_id,
        storage_key=storage_key,
        file_size=file_size,
        keywords=[],
        upload_status="completed",
        upload_progress=100,
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(paper)

    # Create processing task
    task_id = str(uuid4())

    task = ProcessingTask(
        id=task_id,
        paper_id=paper_id,
        status="pending",
        storage_key=storage_key,
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    logger.info(
        "Direct upload completed",
        user_id=user_id,
        paper_id=paper_id,
        filename=filename,
        file_size=file_size,
    )

    return PaperCreateResponse(
        success=True,
        data={
            "paperId": paper_id,
            "taskId": task_id,
            "status": "processing",
            "message": "File uploaded successfully. Processing started.",
        },
    )


@router.get("/{paper_id}")
async def get_paper(
    request: Request,
    paper_id: str,
    includeChunks: Optional[bool] = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paper details.

    Path parameters:
        paper_id: Paper ID

    Query parameters:
        includeChunks: Include paper chunks in response

    Returns:
        Paper metadata and optionally chunks.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query paper with user isolation
    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.id == paper_id)
        .where(Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper, task = row
    paper_dict = _format_paper_response(paper, task)

    # Include chunks if requested
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


@router.get("/{paper_id}/status")
async def get_paper_status(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paper processing status.

    Path parameters:
        paper_id: Paper ID

    Returns:
        Processing status and progress.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query paper with processing task
    query = (
        select(Paper, ProcessingTask)
        .outerjoin(ProcessingTask, Paper.id == ProcessingTask.paper_id)
        .where(Paper.id == paper_id)
        .where(Paper.user_id == user_id)
    )

    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper, task = row

    processing_status = task.status if task else paper.status or "pending"
    progress = _get_progress_percent(processing_status)
    stage = _get_processing_stage(processing_status)

    return {
        "success": True,
        "data": {
            "paperId": paper_id,
            "status": processing_status,
            "progress": progress,
            "stage": stage,
            "errorMessage": task.error_message if task else None,
            "storageKey": paper.storage_key,
            "updatedAt": task.updated_at.isoformat() if task and task.updated_at else None,
            "completedAt": task.completed_at.isoformat() if task and task.completed_at else None,
        },
    }


@router.patch("/{paper_id}")
async def update_paper(
    request: Request,
    paper_id: str,
    body: PaperUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update paper metadata.

    Path parameters:
        paper_id: Paper ID

    Request body:
        title: New title
        authors: List of authors
        year: Publication year
        abstract: Paper abstract
        keywords: List of keywords
        starred: Starred status
        projectId: Project ID

    Returns:
        Updated paper data.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify paper exists and belongs to user
    existing_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    existing_result = await db.execute(existing_query)
    paper = existing_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Apply updates
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

    paper.updated_at = datetime.now(timezone.utc)

    # Refresh to get updated data
    await db.refresh(paper)

    logger.info(
        "Paper updated",
        user_id=user_id,
        paper_id=paper_id,
        fields_updated=sum(1 for f in [body.title, body.authors, body.year, body.abstract, body.keywords, body.starred, body.projectId] if f is not None),
    )

    return {"success": True, "data": _format_paper_response(paper)}


@router.delete("/{paper_id}")
async def delete_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a paper.

    Path parameters:
        paper_id: Paper ID

    Returns:
        Success message.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify paper exists and belongs to user
    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Delete file from storage
    storage_key = paper.storage_key
    if storage_key:
        import os
        local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        file_path = os.path.join(local_storage_path, storage_key)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete paper (cascade will delete related records)
    await db.delete(paper)

    logger.info(
        "Paper deleted",
        user_id=user_id,
        paper_id=paper_id,
    )

    return {"success": True, "data": {"message": "Paper deleted successfully"}}


@router.patch("/{paper_id}/starred")
async def toggle_starred(
    request: Request,
    paper_id: str,
    body: StarredRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle paper starred status.

    Path parameters:
        paper_id: Paper ID

    Request body:
        starred: New starred status

    Returns:
        Updated paper data.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify paper exists and belongs to user
    existing_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    existing_result = await db.execute(existing_query)
    paper = existing_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Update starred status
    paper.starred = body.starred
    paper.updated_at = datetime.now(timezone.utc)

    await db.refresh(paper)

    return {"success": True, "data": _format_paper_response(paper)}


@router.get("/{paper_id}/download")
async def download_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download paper PDF file.

    Path parameters:
        paper_id: Paper ID

    Returns:
        PDF file stream.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Query paper with user isolation
    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    storage_key = paper.storage_key
    if not storage_key:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="No file associated with this paper",
            instance=instance,
        )

    # Get file from storage
    import os
    local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
    file_path = os.path.join(local_storage_path, storage_key)

    if not os.path.exists(file_path):
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="File not found in storage",
            instance=instance,
        )

    # Stream file
    from fastapi.responses import FileResponse

    filename = f"{paper.title or 'paper'}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/{paper_id}/chunks")
async def get_paper_chunks(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paper chunks for reading.

    Path parameters:
        paper_id: Paper ID

    Returns:
        List of paper chunks with content.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify paper exists and belongs to user
    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Query chunks
    chunks_query = (
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.page_start, PaperChunk.id)
    )
    chunks_result = await db.execute(chunks_query)
    chunks = chunks_result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": c.id,
                "content": c.content,
                "section": c.section,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "is_table": c.is_table,
                "is_figure": c.is_figure,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chunks
        ],
    }


@router.post("/{paper_id}/regenerate-chunks")
async def regenerate_chunks(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger chunk regeneration for a paper.

    Path parameters:
        paper_id: Paper ID

    Returns:
        Task ID for tracking.
    """
    instance = str(request.url.path)
    user_id = current_user.id

    # Verify paper exists and belongs to user
    paper_query = select(Paper).where(
        Paper.id == paper_id,
        Paper.user_id == user_id,
    )
    paper_result = await db.execute(paper_query)
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Check for existing task and update or create new
    existing_task_query = select(ProcessingTask).where(
        ProcessingTask.paper_id == paper_id,
    )
    existing_task_result = await db.execute(existing_task_query)
    existing_task = existing_task_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing_task:
        # Update existing task
        existing_task.status = "pending"
        existing_task.error_message = None
        existing_task.updated_at = now
        task_id = existing_task.id
    else:
        # Create new task
        task_id = str(uuid4())
        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=paper.storage_key,
            created_at=now,
            updated_at=now,
        )
        db.add(task)

    logger.info(
        "Chunk regeneration triggered",
        user_id=user_id,
        paper_id=paper_id,
        task_id=task_id,
    )

    return {
        "success": True,
        "data": {
            "taskId": task_id,
            "message": "Chunk regeneration triggered",
        },
    }


__all__ = ["router"]