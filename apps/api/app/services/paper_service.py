"""Paper business logic service layer.

Provides CRUD operations for papers:
- list_papers: Paginated list with filters
- get_paper: Single paper with ownership check
- create_paper: Create paper record
- update_paper: Update paper metadata
- delete_paper: Delete paper with ownership check
- search_papers: Full-text search
- toggle_star: Toggle starred status

Per D-04: Service layer for business logic separation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.annotation import Annotation
from app.models.paper import Paper, PaperChunk
from app.models.reading_progress import ReadingProgress
from app.models.task import ProcessingTask
from app.models.upload_history import UploadHistory
from app.repositories.paper_repository import PaperRepository
from app.services.reading_card_service import ensure_reading_card_doc
from app.services.storage_service import get_storage_service
from app.utils.logger import logger
from app.utils.problem_detail import ErrorTypes, ProblemDetail, create_error


class PaperService:
    """Service class for paper business logic.

    All methods are async and use SQLAlchemy AsyncSession.
    Includes proper error handling and logging.
    """

    @staticmethod
    async def list_papers(
        db: AsyncSession,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """List papers for a user with filters and pagination.

        Args:
            db: AsyncSession database connection
            user_id: User ID (owner of papers)
            filters: Optional filters:
                - status: Paper status (pending, processing, completed, failed)
                - starred: Boolean filter for starred papers
                - project_id: Filter by project
                - search: Full-text search query
            pagination: Optional pagination:
                - page: Page number (default 1)
                - limit: Items per page (default 20)
                - sort_by: Sort field (default createdAt)
                - sort_order: asc or desc (default desc)

        Returns:
            Dictionary with items and pagination info:
                {
                    "items": [...],
                    "pagination": {
                        "page": 1,
                        "limit": 20,
                        "total": 100,
                        "totalPages": 5
                    }
                }
        """
        filters = filters or {}
        pagination = pagination or {}

        page = pagination.get("page", 1)
        limit = min(pagination.get("limit", 20), 100)  # Max 100 per page
        sort_by = pagination.get("sort_by", "created_at")
        sort_order = pagination.get("sort_order", "desc")

        # Build base query
        query = select(Paper).where(Paper.user_id == user_id)

        # Apply filters
        if "status" in filters:
            query = query.where(Paper.status == filters["status"])

        if "starred" in filters:
            query = query.where(Paper.starred == filters["starred"])

        if "project_id" in filters:
            query = query.where(Paper.project_id == filters["project_id"])

        if "search" in filters and filters["search"]:
            search_term = f"%{filters['search']}%"
            query = query.where(
                or_(
                    Paper.title.ilike(search_term),
                    Paper.abstract.ilike(search_term),
                    func.array_to_string(Paper.authors, ",").ilike(search_term),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Paper, sort_by, Paper.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db.execute(query)
        papers = result.scalars().all()

        total_pages = (total + limit - 1) // limit

        logger.info(
            "Papers listed",
            user_id=user_id,
            total=total,
            page=page,
            filters=filters,
        )

        return {
            "items": papers,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
            },
        }

    @staticmethod
    async def get_paper(
        db: AsyncSession,
        paper_id: str,
        user_id: str,
    ) -> Optional[Paper]:
        """Get a single paper with ownership check.

        Args:
            db: AsyncSession database connection
            paper_id: Paper ID
            user_id: User ID (for ownership verification)

        Returns:
            Paper object if found and owned by user

        Raises:
            ValueError: If paper not found or not owned by user
        """
        query = (
            select(Paper)
            .options(
                selectinload(Paper.paper_chunks),
                selectinload(Paper.annotations),
                selectinload(Paper.reading_progress),
            )
            .where(Paper.id == paper_id, Paper.user_id == user_id)
        )

        result = await db.execute(query)
        paper = result.scalar_one_or_none()

        if not paper:
            logger.warning(
                "Paper not found or not owned",
                paper_id=paper_id,
                user_id=user_id,
            )
            raise ValueError("Paper not found")

        logger.info("Paper retrieved", paper_id=paper_id, user_id=user_id)
        return paper

    @staticmethod
    async def create_paper(
        db: AsyncSession,
        user_id: str,
        data: Dict[str, Any],
    ) -> Paper:
        """Create a new paper record.

        Args:
            db: AsyncSession database connection
            user_id: User ID (owner)
            data: Paper data dictionary with fields:
                - title: Required
                - authors: Optional list of author names
                - year: Optional publication year
                - abstract: Optional abstract text
                - doi: Optional DOI
                - arxiv_id: Optional arXiv ID
                - storage_key: Optional storage key for PDF
                - file_size: Optional file size in bytes

        Returns:
            Created Paper object
        """
        paper_id = str(uuid4())
        now = datetime.now(timezone.utc)

        paper = Paper(
            id=paper_id,
            title=data.get("title", "Untitled"),
            authors=data.get("authors", []),
            year=data.get("year"),
            abstract=data.get("abstract"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            storage_key=data.get("storage_key"),
            file_size=data.get("file_size"),
            status="pending",
            user_id=user_id,
            starred=False,
            created_at=now,
            updated_at=now,
        )

        db.add(paper)
        await db.flush()  # Get the ID without committing

        logger.info(
            "Paper created",
            paper_id=paper_id,
            user_id=user_id,
            title=paper.title,
        )

        return paper

    @staticmethod
    async def update_paper(
        db: AsyncSession,
        paper_id: str,
        user_id: str,
        data: Dict[str, Any],
    ) -> Paper:
        """Update paper metadata.

        Args:
            db: AsyncSession database connection
            paper_id: Paper ID
            user_id: User ID (for ownership verification)
            data: Update data with fields:
                - title: Optional new title
                - authors: Optional new authors list
                - year: Optional new year
                - abstract: Optional new abstract
                - starred: Optional starred status
                - project_id: Optional project ID

        Returns:
            Updated Paper object

        Raises:
            ValueError: If paper not found or not owned by user
        """
        # Get paper with ownership check
        paper = await PaperService.get_paper(db, paper_id, user_id)

        # Update fields
        updatable_fields = [
            "title",
            "authors",
            "year",
            "abstract",
            "doi",
            "arxiv_id",
            "starred",
            "project_id",
            "reading_notes",
            "keywords",
            "venue",
        ]

        for field in updatable_fields:
            if field in data:
                setattr(paper, field, data[field])

        paper.updated_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info(
            "Paper updated",
            paper_id=paper_id,
            user_id=user_id,
            updated_fields=list(data.keys()),
        )

        return paper

    @staticmethod
    async def delete_paper(
        db: AsyncSession,
        paper_id: str,
        user_id: str,
    ) -> bool:
        """Delete a paper with ownership check.

        Args:
            db: AsyncSession database connection
            paper_id: Paper ID
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If paper not found or not owned by user
        """
        # Get paper with ownership check (raises ValueError if not found)
        paper = await PaperService.get_paper(db, paper_id, user_id)

        # Delete paper (cascade handles related entities)
        await db.delete(paper)

        logger.info(
            "Paper deleted",
            paper_id=paper_id,
            user_id=user_id,
        )

        return True

    @staticmethod
    async def search_papers(
        db: AsyncSession,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Paper]:
        """Full-text search on papers.

        Args:
            db: AsyncSession database connection
            user_id: User ID (owner of papers)
            query: Search query string
            filters: Optional filters:
                - year_min: Minimum year
                - year_max: Maximum year
                - status: Paper status
                - starred: Boolean filter

        Returns:
            List of matching Paper objects
        """
        filters = filters or {}

        # Build search query
        search_term = f"%{query}%"
        sql_query = select(Paper).where(
            Paper.user_id == user_id,
            or_(
                Paper.title.ilike(search_term),
                Paper.abstract.ilike(search_term),
                func.array_to_string(Paper.authors, ",").ilike(search_term),
                func.array_to_string(Paper.keywords, ",").ilike(search_term),
            ),
        )

        # Apply additional filters
        if "year_min" in filters:
            sql_query = sql_query.where(Paper.year >= filters["year_min"])

        if "year_max" in filters:
            sql_query = sql_query.where(Paper.year <= filters["year_max"])

        if "status" in filters:
            sql_query = sql_query.where(Paper.status == filters["status"])

        if "starred" in filters:
            sql_query = sql_query.where(Paper.starred == filters["starred"])

        # Execute query
        result = await db.execute(sql_query)
        papers = result.scalars().all()

        logger.info(
            "Papers searched",
            user_id=user_id,
            query=query,
            results_count=len(papers),
        )

        return list(papers)

    @staticmethod
    async def toggle_star(
        db: AsyncSession,
        paper_id: str,
        user_id: str,
        starred: bool,
    ) -> Paper:
        """Toggle paper starred status.

        Args:
            db: AsyncSession database connection
            paper_id: Paper ID
            user_id: User ID (for ownership verification)
            starred: New starred status

        Returns:
            Updated Paper object

        Raises:
            ValueError: If paper not found or not owned by user
        """
        # Get paper with ownership check
        paper = await PaperService.get_paper(db, paper_id, user_id)

        # Update starred status
        paper.starred = starred
        paper.updated_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info(
            "Paper star toggled",
            paper_id=paper_id,
            user_id=user_id,
            starred=starred,
        )

        return paper

    @staticmethod
    async def list_papers_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        page: int,
        limit: int,
        starred: Optional[bool] = None,
        read_status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        papers, total = await PaperRepository.list_papers(
            db,
            user_id,
            page=page,
            limit=limit,
            starred=starred,
            read_status=read_status,
            date_from=date_from,
            date_to=date_to,
        )

        paper_ids = [paper.id for paper in papers]
        task_map: Dict[str, ProcessingTask] = {}
        if paper_ids:
            task_result = await db.execute(
                select(ProcessingTask).where(ProcessingTask.paper_id.in_(paper_ids))
            )
            tasks = task_result.scalars().all()
            task_map = {task.paper_id: task for task in tasks}

        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return {
            "papers": papers,
            "task_map": task_map,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    @staticmethod
    async def search_papers_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        query_text: str,
        page: int,
        limit: int,
    ) -> Dict[str, Any]:
        papers, total = await PaperRepository.search_papers(
            db,
            user_id,
            query_text=query_text,
            page=page,
            limit=limit,
        )

        paper_ids = [paper.id for paper in papers]
        task_map: Dict[str, ProcessingTask] = {}
        if paper_ids:
            task_result = await db.execute(
                select(ProcessingTask).where(ProcessingTask.paper_id.in_(paper_ids))
            )
            tasks = task_result.scalars().all()
            task_map = {task.paper_id: task for task in tasks}

        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return {
            "papers": papers,
            "task_map": task_map,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "query": query_text,
        }

    @staticmethod
    async def get_paper_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        paper_id: str,
        include_chunks: bool,
    ) -> Dict[str, Any]:
        paper = await PaperRepository.get_user_paper(db, user_id, paper_id)
        if not paper:
            raise ValueError("Paper not found")

        task_result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.paper_id == paper_id)
        )
        task = task_result.scalar_one_or_none()

        chunks: List[PaperChunk] = []
        if include_chunks or not paper.reading_card_doc:
            chunks = await PaperRepository.list_chunks(db, paper_id)

        if not paper.reading_card_doc:
            reading_card_doc = ensure_reading_card_doc(paper, records=chunks)
            if reading_card_doc is not None:
                await db.flush()

        return {
            "paper": paper,
            "task": task,
            "chunks": chunks if include_chunks else [],
        }

    @staticmethod
    async def create_paper_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        filename: str,
    ) -> Dict[str, Any]:
        title = filename.replace(".pdf", "").replace(".PDF", "")
        existing = await PaperRepository.get_user_paper_by_title(db, user_id, title)
        if existing:
            raise ValueError(f'Duplicate paper title: {title}')

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

        upload_history = UploadHistory(
            id=str(uuid4()),
            user_id=user_id,
            filename=filename,
            status="PROCESSING",
            created_at=now,
            updated_at=now,
        )
        db.add(upload_history)

        return {
            "paperId": paper_id,
            "uploadUrl": f"/api/v1/papers/upload/local/{storage_key}",
            "storageKey": storage_key,
            "expiresIn": 3600,
        }

    @staticmethod
    async def update_paper_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        paper_id: str,
        updates: Dict[str, Any],
    ) -> Paper:
        paper = await PaperRepository.get_user_paper(db, user_id, paper_id)
        if not paper:
            raise ValueError("Paper not found")

        field_mapping = {
            "title": "title",
            "authors": "authors",
            "year": "year",
            "abstract": "abstract",
            "keywords": "keywords",
            "starred": "starred",
            "projectId": "project_id",
            "readingNotes": "reading_notes",
        }

        for req_field, model_field in field_mapping.items():
            if req_field in updates and updates[req_field] is not None:
                setattr(paper, model_field, updates[req_field])

        paper.updated_at = datetime.now(timezone.utc)
        return paper

    @staticmethod
    async def delete_paper_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        paper_id: str,
    ) -> None:
        paper = await PaperRepository.get_user_paper(db, user_id, paper_id)
        if not paper:
            raise ValueError("Paper not found")

        storage_key = paper.storage_key
        await db.delete(paper)

        if storage_key:
            storage_service = get_storage_service()
            try:
                await storage_service.delete_file(storage_key)
            except Exception as e:
                # DB deletion takes precedence; file cleanup failure is logged for follow-up.
                logger.warning(
                    "Paper file cleanup failed after DB delete",
                    paper_id=paper_id,
                    storage_key=storage_key,
                    error=str(e),
                )

    @staticmethod
    async def batch_delete_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        paper_ids: List[str],
    ) -> int:
        papers = await PaperRepository.list_user_papers_by_ids(db, user_id, paper_ids)
        storage_keys_to_delete: List[str] = []
        deleted_count = 0
        for paper in papers:
            storage_key = paper.storage_key
            if storage_key:
                storage_keys_to_delete.append(storage_key)
            await db.delete(paper)
            deleted_count += 1

        if storage_keys_to_delete:
            storage_service = get_storage_service()
            for storage_key in storage_keys_to_delete:
                try:
                    await storage_service.delete_file(storage_key)
                except Exception as e:
                    logger.warning(
                        "Batch paper file cleanup failed after DB delete",
                        storage_key=storage_key,
                        error=str(e),
                    )

        return deleted_count

    @staticmethod
    async def batch_star_for_api(
        db: AsyncSession,
        user_id: str,
        *,
        paper_ids: List[str],
        starred: bool,
    ) -> int:
        papers = await PaperRepository.list_user_papers_by_ids(db, user_id, paper_ids)
        for paper in papers:
            paper.starred = starred
            paper.updated_at = datetime.now(timezone.utc)
        return len(papers)


__all__ = ["PaperService"]
