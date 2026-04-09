"""Paper management API routes.

Migrated from Node.js papers.ts - provides full CRUD operations for papers.

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

from app.deps import get_current_user, postgres_db
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

    # Build where clause
    where_clauses = [f"p.user_id = '{user_id}'"]
    params = []

    # Starred filter
    if starred is not None:
        if starred.lower() == "true":
            where_clauses.append("p.starred = true")
        elif starred.lower() == "false":
            where_clauses.append("p.starred = false")

    # Date range filter
    if dateFrom:
        where_clauses.append(f"p.created_at >= '{dateFrom}'")
    if dateTo:
        where_clauses.append(f"p.created_at <= '{dateTo}'")

    where_sql = " AND ".join(where_clauses)

    # Query papers with processing tasks
    if readStatus in ("in-progress", "completed"):
        # Complex query with reading progress join
        if readStatus == "in-progress":
            progress_condition = "rp.current_page > 0 AND rp.current_page < COALESCE(rp.total_pages, 999999)"
        else:
            progress_condition = "rp.current_page >= COALESCE(rp.total_pages, 0)"

        query = f"""
            SELECT p.*,
                   pt.status as processing_status,
                   pt.error_message as processing_error,
                   pt.updated_at as last_updated
            FROM papers p
            LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
            INNER JOIN reading_progress rp ON p.id = rp.paper_id
            WHERE {where_sql}
              AND rp.user_id = '{user_id}'
              AND {progress_condition}
            ORDER BY p.created_at DESC
            LIMIT {limit} OFFSET {offset}
        """
    else:
        # Standard query without reading progress join
        if readStatus == "unread":
            where_sql += " AND NOT EXISTS (SELECT 1 FROM reading_progress rp WHERE rp.paper_id = p.id AND rp.user_id = '{user_id}')"

        query = f"""
            SELECT p.*,
                   pt.status as processing_status,
                   pt.error_message as processing_error,
                   pt.updated_at as last_updated
            FROM papers p
            LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
            WHERE {where_sql}
            ORDER BY p.created_at DESC
            LIMIT {limit} OFFSET {offset}
        """

    papers = await postgres_db.fetch(query)

    # Get total count
    count_query = f"SELECT COUNT(*) as count FROM papers p WHERE {where_sql}"
    total_result = await postgres_db.fetchrow(count_query)
    total = total_result["count"] if total_result else 0

    # Format response
    formatted_papers = []
    for paper in papers:
        paper_dict = dict(paper)
        processing_status = paper_dict.pop("processing_status", None) or paper_dict.get("status", "pending")
        paper_dict["processingStatus"] = processing_status
        paper_dict["progress"] = _get_progress_percent(processing_status)
        paper_dict["processingError"] = paper_dict.pop("processing_error", None)
        formatted_papers.append(paper_dict)

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
    search_term = q.replace("'", "''")  # Escape single quotes

    query = f"""
        SELECT p.*,
               pt.status as processing_status,
               pt.error_message as processing_error,
               pt.updated_at as last_updated
        FROM papers p
        LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
        WHERE p.user_id = '{user_id}'
          AND (
            LOWER(p.title) LIKE LOWER('%{search_term}%')
            OR EXISTS (
                SELECT 1 FROM unnest(p.authors) a WHERE LOWER(a) LIKE LOWER('%{search_term}%')
            )
            OR LOWER(p.abstract) LIKE LOWER('%{search_term}%')
          )
        ORDER BY p.created_at DESC
        LIMIT {limit} OFFSET {offset}
    """

    papers = await postgres_db.fetch(query)

    # Get total count
    count_query = f"""
        SELECT COUNT(*) as count
        FROM papers p
        WHERE p.user_id = '{user_id}'
          AND (
            LOWER(p.title) LIKE LOWER('%{search_term}%')
            OR EXISTS (
                SELECT 1 FROM unnest(p.authors) a WHERE LOWER(a) LIKE LOWER('%{search_term}%')
            )
            OR LOWER(p.abstract) LIKE LOWER('%{search_term}%')
          )
    """
    total_result = await postgres_db.fetchrow(count_query)
    total = total_result["count"] if total_result else 0

    # Format response
    formatted_papers = []
    for paper in papers:
        paper_dict = dict(paper)
        processing_status = paper_dict.pop("processing_status", None) or paper_dict.get("status", "pending")
        paper_dict["processingStatus"] = processing_status
        paper_dict["progress"] = _get_progress_percent(processing_status)
        paper_dict["processingError"] = paper_dict.pop("processing_error", None)
        formatted_papers.append(paper_dict)

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
    existing = await postgres_db.fetchrow(
        "SELECT id, status FROM papers WHERE user_id = $1 AND title = $2",
        user_id,
        title,
    )

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
    from datetime import datetime
    storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid4()}.pdf"

    # Create paper record
    paper_id = str(uuid4())
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        INSERT INTO papers (id, title, authors, status, user_id, storage_key, keywords, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        paper_id,
        title,
        [],
        "pending",
        user_id,
        storage_key,
        [],
        now,
        now,
    )

    # Create upload history record
    upload_history_id = str(uuid4())
    await postgres_db.execute(
        """
        INSERT INTO upload_history (id, user_id, filename, status, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        upload_history_id,
        user_id,
        filename,
        "PROCESSING",
        now,
        now,
    )

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
    paper = await postgres_db.fetchrow(
        "SELECT id, batch_id FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Check if task already exists
    existing_task = await postgres_db.fetchrow(
        "SELECT id FROM processing_tasks WHERE paper_id = $1",
        paper_id,
    )

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

    await postgres_db.execute(
        """
        INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        paper_id,
        "pending",
        storage_key,
        now,
        now,
    )

    # Update paper status
    await postgres_db.execute(
        """
        UPDATE papers
        SET status = 'processing',
            upload_status = 'completed',
            upload_progress = 100,
            uploaded_at = $1,
            updated_at = $2
        WHERE id = $3
        """,
        now,
        now,
        paper_id,
    )

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
    existing = await postgres_db.fetchrow(
        "SELECT id FROM papers WHERE user_id = $1 AND title = $2",
        user_id,
        title,
    )

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

    await postgres_db.execute(
        """
        INSERT INTO papers (id, title, authors, status, user_id, storage_key, file_size, keywords,
                           upload_status, upload_progress, uploaded_at, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
        paper_id,
        title,
        [],
        "processing",
        user_id,
        storage_key,
        file_size,
        [],
        "completed",
        100,
        now,
        now,
        now,
    )

    # Create processing task
    task_id = str(uuid4())

    await postgres_db.execute(
        """
        INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        paper_id,
        "pending",
        storage_key,
        now,
        now,
    )

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
    paper = await postgres_db.fetchrow(
        """
        SELECT p.*,
               pt.status as processing_status,
               pt.error_message as processing_error
        FROM papers p
        LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
        WHERE p.id = $1 AND p.user_id = $2
        """,
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    paper_dict = dict(paper)
    processing_status = paper_dict.pop("processing_status", None) or paper_dict.get("status", "pending")
    paper_dict["processingStatus"] = processing_status
    paper_dict["progress"] = _get_progress_percent(processing_status)
    paper_dict["processingError"] = paper_dict.pop("processing_error", None)

    # Include chunks if requested
    if includeChunks:
        chunks = await postgres_db.fetch(
            """
            SELECT id, content, section, page_start, page_end, is_table, is_figure
            FROM paper_chunks
            WHERE paper_id = $1
            ORDER BY page_start, id
            """,
            paper_id,
        )
        paper_dict["chunks"] = [dict(c) for c in chunks]

    return {"success": True, "data": paper_dict}


@router.get("/{paper_id}/status")
async def get_paper_status(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
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
    paper = await postgres_db.fetchrow(
        """
        SELECT p.id, p.status, p.storage_key,
               pt.status as task_status,
               pt.error_message,
               pt.updated_at,
               pt.completed_at
        FROM papers p
        LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
        WHERE p.id = $1 AND p.user_id = $2
        """,
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    processing_status = paper["task_status"] or paper["status"] or "pending"
    progress = _get_progress_percent(processing_status)
    stage = _get_processing_stage(processing_status)

    return {
        "success": True,
        "data": {
            "paperId": paper_id,
            "status": processing_status,
            "progress": progress,
            "stage": stage,
            "errorMessage": paper["error_message"],
            "storageKey": paper["storage_key"],
            "updatedAt": paper["updated_at"].isoformat() if paper["updated_at"] else None,
            "completedAt": paper["completed_at"].isoformat() if paper["completed_at"] else None,
        },
    }


@router.patch("/{paper_id}")
async def update_paper(
    request: Request,
    paper_id: str,
    body: PaperUpdateRequest,
    current_user: User = Depends(get_current_user),
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
    existing = await postgres_db.fetchrow(
        "SELECT id FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not existing:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Build update query
    updates = []
    params = []
    param_idx = 1

    if body.title is not None:
        updates.append(f"title = ${param_idx}")
        params.append(body.title)
        param_idx += 1

    if body.authors is not None:
        updates.append(f"authors = ${param_idx}")
        params.append(body.authors)
        param_idx += 1

    if body.year is not None:
        updates.append(f"year = ${param_idx}")
        params.append(body.year)
        param_idx += 1

    if body.abstract is not None:
        updates.append(f"abstract = ${param_idx}")
        params.append(body.abstract)
        param_idx += 1

    if body.keywords is not None:
        updates.append(f"keywords = ${param_idx}")
        params.append(body.keywords)
        param_idx += 1

    if body.starred is not None:
        updates.append(f"starred = ${param_idx}")
        params.append(body.starred)
        param_idx += 1

    if body.projectId is not None:
        updates.append(f"project_id = ${param_idx}")
        params.append(body.projectId)
        param_idx += 1

    if not updates:
        # No updates, just return existing paper
        paper = await postgres_db.fetchrow(
            "SELECT * FROM papers WHERE id = $1",
            paper_id,
        )
        return {"success": True, "data": dict(paper)}

    # Add updated_at
    updates.append(f"updated_at = ${param_idx}")
    params.append(datetime.now(timezone.utc))
    param_idx += 1

    # Add paper_id to params
    params.append(paper_id)

    query = f"UPDATE papers SET {', '.join(updates)} WHERE id = ${param_idx}"
    await postgres_db.execute(query, *params)

    # Fetch updated paper
    paper = await postgres_db.fetchrow(
        "SELECT * FROM papers WHERE id = $1",
        paper_id,
    )

    logger.info(
        "Paper updated",
        user_id=user_id,
        paper_id=paper_id,
        fields_updated=len(updates) - 1,  # Exclude updated_at
    )

    return {"success": True, "data": dict(paper)}


@router.delete("/{paper_id}")
async def delete_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
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
    paper = await postgres_db.fetchrow(
        "SELECT id, storage_key FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Delete file from storage
    storage_key = paper["storage_key"]
    if storage_key:
        import os
        local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        file_path = os.path.join(local_storage_path, storage_key)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete paper (cascade will delete related records)
    await postgres_db.execute(
        "DELETE FROM papers WHERE id = $1",
        paper_id,
    )

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
    existing = await postgres_db.fetchrow(
        "SELECT id FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not existing:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Update starred status
    await postgres_db.execute(
        """
        UPDATE papers
        SET starred = $1, updated_at = $2
        WHERE id = $3
        """,
        body.starred,
        datetime.now(timezone.utc),
        paper_id,
    )

    # Fetch updated paper
    paper = await postgres_db.fetchrow(
        "SELECT * FROM papers WHERE id = $1",
        paper_id,
    )

    return {"success": True, "data": dict(paper)}


@router.get("/{paper_id}/download")
async def download_paper(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
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
    paper = await postgres_db.fetchrow(
        "SELECT id, storage_key, title FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    storage_key = paper["storage_key"]
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

    filename = f"{paper['title'] or 'paper'}.pdf"

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
    paper = await postgres_db.fetchrow(
        "SELECT id FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Query chunks
    chunks = await postgres_db.fetch(
        """
        SELECT id, content, section, page_start, page_end, is_table, is_figure, created_at
        FROM paper_chunks
        WHERE paper_id = $1
        ORDER BY page_start, id
        """,
        paper_id,
    )

    return {
        "success": True,
        "data": [dict(c) for c in chunks],
    }


@router.post("/{paper_id}/regenerate-chunks")
async def regenerate_chunks(
    request: Request,
    paper_id: str,
    current_user: User = Depends(get_current_user),
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
    paper = await postgres_db.fetchrow(
        "SELECT id, storage_key FROM papers WHERE id = $1 AND user_id = $2",
        paper_id,
        user_id,
    )

    if not paper:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="Paper not found",
            instance=instance,
        )

    # Create a new processing task
    task_id = str(uuid4())
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (paper_id) DO UPDATE SET
            status = 'pending',
            error_message = NULL,
            updated_at = $5
        """,
        task_id,
        paper_id,
        "pending",
        paper["storage_key"],
        now,
        now,
    )

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