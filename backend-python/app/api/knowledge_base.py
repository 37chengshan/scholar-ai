"""Knowledge Base API endpoints.

Provides RESTful endpoints for Knowledge Base (KB) management:
- KB CRUD: create, list, get, update, delete
- KB paper management: list papers, add paper, remove paper
- KB import: upload PDF, import from URL/DOI/arXiv, batch upload
- KB search: vector search within KB
- KB chat: SSE streaming for agentic Q&A

Per D-07: KB专用API，不复用 papers/projects。
Per D-08: KB全局固定配置，导入论文继承KB配置。
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper, PaperChunk
from app.models.task import ProcessingTask
from app.models.upload_history import UploadHistory
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class KBCreate(BaseModel):
    """Request to create a knowledge base."""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None)
    embeddingModel: str = Field(default="bge-m3")
    parseEngine: str = Field(default="docling")
    chunkStrategy: str = Field(default="by-paragraph")
    enableGraph: bool = Field(default=False)
    enableImrad: bool = Field(default=True)
    enableChartUnderstanding: bool = Field(default=False)
    enableMultimodalSearch: bool = Field(default=False)
    enableComparison: bool = Field(default=False)


class KBUpdate(BaseModel):
    """Request to update a knowledge base.

    Config fields are not updateable after creation (per D-08).
    """

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = None


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBListResponse(BaseModel):
    """Response wrapper for KB list."""

    success: bool = True
    data: Dict[str, Any]


class KBPaperAdd(BaseModel):
    """Request to add paper to KB."""

    paperId: str


class KBImportUrl(BaseModel):
    """Request to import paper from URL/DOI."""

    url: str


class KBImportArxiv(BaseModel):
    """Request to import paper from arXiv."""

    arxivId: str


class KBSearch(BaseModel):
    """Request for KB vector search."""

    query: str
    topK: int = Field(default=10, ge=1, le=50)


class KBBatchDelete(BaseModel):
    """Request to batch delete KBs."""

    ids: List[str]


class KBBatchExport(BaseModel):
    """Request to batch export KBs."""

    ids: List[str]


# =============================================================================
# Helper Functions
# =============================================================================


def _format_kb_response(kb: KnowledgeBase) -> dict:
    """Format KB for API response with camelCase fields."""
    return {
        "id": kb.id,
        "userId": kb.user_id,
        "name": kb.name,
        "description": kb.description or "",
        "category": kb.category or "其他",
        "paperCount": kb.paper_count,
        "chunkCount": kb.chunk_count,
        "entityCount": kb.entity_count,
        "embeddingModel": kb.embedding_model,
        "parseEngine": kb.parse_engine,
        "chunkStrategy": kb.chunk_strategy,
        "enableGraph": kb.enable_graph,
        "enableImrad": kb.enable_imrad,
        "enableChartUnderstanding": kb.enable_chart_understanding,
        "enableMultimodalSearch": kb.enable_multimodal_search,
        "enableComparison": kb.enable_comparison,
        "createdAt": kb.created_at.isoformat() if kb.created_at else None,
        "updatedAt": kb.updated_at.isoformat() if kb.updated_at else None,
    }


async def _hydrate_kb_stats(db: AsyncSession, kb: KnowledgeBase) -> dict:
    """Build a response payload with live counts where possible."""
    paper_count_result = await db.execute(
        select(func.count(Paper.id)).where(Paper.knowledge_base_id == kb.id)
    )
    paper_count = paper_count_result.scalar() or 0

    chunk_count_result = await db.execute(
        select(func.count(PaperChunk.id))
        .select_from(PaperChunk)
        .join(Paper, PaperChunk.paper_id == Paper.id)
        .where(Paper.knowledge_base_id == kb.id)
    )
    chunk_count = chunk_count_result.scalar() or 0

    latest_paper_update_result = await db.execute(
        select(func.max(Paper.updated_at)).where(Paper.knowledge_base_id == kb.id)
    )
    latest_paper_update = latest_paper_update_result.scalar_one_or_none()

    payload = _format_kb_response(kb)
    payload["paperCount"] = int(paper_count)
    payload["chunkCount"] = int(chunk_count)

    effective_updated_at = kb.updated_at
    if latest_paper_update and (
        effective_updated_at is None or latest_paper_update > effective_updated_at
    ):
        effective_updated_at = latest_paper_update

    payload["updatedAt"] = (
        effective_updated_at.isoformat() if effective_updated_at else None
    )
    return payload


# =============================================================================
# KB CRUD Endpoints
# =============================================================================


@router.get("", response_model=KBListResponse)
async def list_knowledge_bases(
    search: Optional[str] = Query(None, description="Search by name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sortBy: str = Query("createdAt", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """List user's knowledge bases with optional filtering."""
    try:
        # Build query
        query = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)

        # Search filter
        if search:
            query = query.where(
                or_(
                    KnowledgeBase.name.ilike(f"%{search}%"),
                    KnowledgeBase.description.ilike(f"%{search}%"),
                )
            )

        # Category filter
        if category:
            query = query.where(KnowledgeBase.category == category)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        order_func = desc if order == "desc" else lambda x: x
        sort_column = getattr(KnowledgeBase, sortBy, KnowledgeBase.created_at)
        query = query.order_by(order_func(sort_column))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        kbs = result.scalars().all()

        return KBListResponse(
            success=True,
            data={
                "knowledgeBases": [await _hydrate_kb_stats(db, kb) for kb in kbs],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    except Exception as e:
        logger.error("Failed to list knowledge bases", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list knowledge bases: {str(e)}"),
        )


@router.post("", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    request: KBCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base with configuration."""
    try:
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=request.name.strip(),
            description=request.description or "",
            category=request.category or "其他",
            embedding_model=request.embeddingModel,
            parse_engine=request.parseEngine,
            chunk_strategy=request.chunkStrategy,
            enable_graph=request.enableGraph,
            enable_imrad=request.enableImrad,
            enable_chart_understanding=request.enableChartUnderstanding,
            enable_multimodal_search=request.enableMultimodalSearch,
            enable_comparison=request.enableComparison,
            paper_count=0,
            chunk_count=0,
            entity_count=0,
        )

        db.add(kb)
        await db.flush()
        await db.refresh(kb)

        logger.info(
            "Knowledge base created", kb_id=kb.id, user_id=user_id, name=request.name
        )

        return KBResponse(success=True, data=await _hydrate_kb_stats(db, kb))

    except Exception as e:
        logger.error("Failed to create knowledge base", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create knowledge base: {str(e)}"),
        )


@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(
    kb_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific knowledge base by ID."""
    try:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        return KBResponse(success=True, data=await _hydrate_kb_stats(db, kb))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get knowledge base", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get knowledge base: {str(e)}"),
        )


@router.patch("/{kb_id}", response_model=KBResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KBUpdate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge base (name, description, category only)."""
    try:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Update fields (config fields not updateable per D-08)
        if request.name is not None:
            kb.name = request.name.strip()
        if request.description is not None:
            kb.description = request.description
        if request.category is not None:
            kb.category = request.category

        await db.flush()
        await db.refresh(kb)

        logger.info("Knowledge base updated", kb_id=kb_id, user_id=user_id)

        return KBResponse(success=True, data=await _hydrate_kb_stats(db, kb))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update knowledge base", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update knowledge base: {str(e)}"),
        )


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge base (papers will have knowledge_base_id set to null)."""
    try:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        await db.delete(kb)
        logger.info("Knowledge base deleted", kb_id=kb_id, user_id=user_id)

        return {"success": True, "data": {"id": kb_id, "deleted": True}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete knowledge base", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete knowledge base: {str(e)}"),
        )


# =============================================================================
# KB Batch Operations
# =============================================================================


@router.post("/batch-delete", response_model=KBResponse)
async def batch_delete_knowledge_bases(
    request: KBBatchDelete,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Batch delete multiple knowledge bases."""
    try:
        deleted_ids = []
        for kb_id in request.ids:
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
                )
            )
            kb = result.scalar_one_or_none()
            if kb:
                await db.delete(kb)
                deleted_ids.append(kb_id)

        logger.info(
            "Batch deleted knowledge bases", count=len(deleted_ids), user_id=user_id
        )

        return KBResponse(
            success=True, data={"deletedIds": deleted_ids, "count": len(deleted_ids)}
        )

    except Exception as e:
        logger.error("Failed to batch delete knowledge bases", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to batch delete: {str(e)}"),
        )


@router.post("/batch-export", response_model=KBResponse)
async def batch_export_knowledge_bases(
    request: KBBatchExport,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Batch export multiple knowledge bases (returns metadata for export)."""
    try:
        exported = []
        for kb_id in request.ids:
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
                )
            )
            kb = result.scalar_one_or_none()
            if kb:
                exported.append(_format_kb_response(kb))

        logger.info(
            "Batch exported knowledge bases", count=len(exported), user_id=user_id
        )

        return KBResponse(
            success=True, data={"knowledgeBases": exported, "count": len(exported)}
        )

    except Exception as e:
        logger.error("Failed to batch export knowledge bases", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to batch export: {str(e)}"),
        )


# =============================================================================
# KB Paper Management
# =============================================================================


@router.get("/{kb_id}/papers", response_model=KBResponse)
async def list_kb_papers(
    kb_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """List papers in a knowledge base."""
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Query papers in this KB
        query = (
            select(Paper)
            .where(Paper.knowledge_base_id == kb_id, Paper.user_id == user_id)
            .order_by(desc(Paper.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(query)
        papers = result.scalars().all()

        # Get total count
        count_query = select(func.count(Paper.id)).where(
            Paper.knowledge_base_id == kb_id, Paper.user_id == user_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        paper_ids = [paper.id for paper in papers]
        chunk_counts: dict[str, int] = {}
        if paper_ids:
            chunk_count_result = await db.execute(
                select(PaperChunk.paper_id, func.count(PaperChunk.id))
                .where(PaperChunk.paper_id.in_(paper_ids))
                .group_by(PaperChunk.paper_id)
            )
            chunk_counts = {
                row[0]: int(row[1]) for row in chunk_count_result.fetchall()
            }

        return KBResponse(
            success=True,
            data={
                "papers": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "authors": p.authors,
                        "year": p.year,
                        "venue": p.venue,
                        "status": p.status,
                        "chunkCount": chunk_counts.get(p.id, 0),
                        "entityCount": 0,
                        "createdAt": p.created_at.isoformat() if p.created_at else None,
                        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
                    }
                    for p in papers
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list KB papers", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list papers: {str(e)}"),
        )


@router.post("/{kb_id}/papers", response_model=KBResponse)
async def add_paper_to_kb(
    kb_id: str,
    request: KBPaperAdd,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Add an existing paper to a knowledge base."""
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Verify paper ownership
        paper_result = await db.execute(
            select(Paper).where(Paper.id == request.paperId, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

        # Update paper's KB
        paper.knowledge_base_id = kb_id
        kb.paper_count += 1

        await db.flush()

        logger.info("Paper added to KB", paper_id=request.paperId, kb_id=kb_id)

        return KBResponse(
            success=True,
            data={
                "paperId": request.paperId,
                "knowledgeBaseId": kb_id,
                "paperCount": kb.paper_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add paper to KB", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to add paper: {str(e)}"),
        )


@router.delete("/{kb_id}/papers/{paper_id}", response_model=KBResponse)
async def remove_paper_from_kb(
    kb_id: str,
    paper_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Remove a paper from a knowledge base."""
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Verify paper in this KB
        paper_result = await db.execute(
            select(Paper).where(
                Paper.id == paper_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found in this knowledge base"),
            )

        # Remove paper from KB
        paper.knowledge_base_id = None
        kb.paper_count -= 1

        await db.flush()

        logger.info("Paper removed from KB", paper_id=paper_id, kb_id=kb_id)

        return KBResponse(
            success=True,
            data={
                "paperId": paper_id,
                "removed": True,
                "paperCount": kb.paper_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove paper from KB", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to remove paper: {str(e)}"),
        )


# =============================================================================
# KB Import Endpoints (Stub implementations)
# =============================================================================


@router.post("/{kb_id}/upload", response_model=KBResponse)
async def upload_pdf_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF to a knowledge base.

    Per D-08: Paper inherits KB config (embeddingModel, parseEngine, etc.).
    No config fields in request - KB config is used for processing.
    """
    try:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("No file uploaded. Use form field name 'file'"),
            )

        filename = file.filename or "untitled.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Only PDF files are accepted"),
            )

        content = await file.read()
        file_size = len(content)
        max_size = 50 * 1024 * 1024

        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=Errors.validation("File size exceeds 50MB limit"),
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("File is not a valid PDF"),
            )

        title = filename.replace(".pdf", "").replace(".PDF", "")
        existing_query = select(Paper).where(
            Paper.user_id == user_id,
            Paper.title == title,
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=Errors.conflict(
                    f'A paper with title "{title}" already exists in your library.'
                ),
            )

        storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"
        local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        file_path = os.path.join(local_storage_path, storage_key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        async with aiofiles.open(file_path, "wb") as output_file:
            await output_file.write(content)

        paper_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
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
            knowledge_base_id=kb_id,
            upload_status="processing",
            upload_progress=0,
            uploaded_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(paper)

        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=storage_key,
            created_at=now,
            updated_at=now,
        )
        db.add(task)

        upload_history = UploadHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            paper_id=paper_id,
            filename=filename,
            status="PROCESSING",
            created_at=now,
            updated_at=now,
        )
        db.add(upload_history)

        kb.paper_count += 1
        kb.updated_at = now

        logger.info(
            "Paper uploaded directly to knowledge base",
            user_id=user_id,
            kb_id=kb_id,
            paper_id=paper_id,
            filename=filename,
            file_size=file_size,
        )

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "paperId": paper_id,
                "taskId": task_id,
                "status": "processing",
                "message": "File uploaded successfully. Processing started.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload PDF to knowledge base", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to upload PDF: {str(e)}"),
        )


@router.post("/{kb_id}/import-url", response_model=KBResponse)
async def import_from_url(
    kb_id: str,
    request: KBImportUrl,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from URL/DOI.

    Per D-08: Paper inherits KB config. Request contains only url field.
    Processing uses KB's stored embedding_model, parse_engine, etc.
    """
    # Stub - will fetch KB and use kb config for processing
    return KBResponse(
        success=True,
        data={"message": "Import URL endpoint - to be implemented", "url": request.url},
    )


@router.post("/{kb_id}/import-arxiv", response_model=KBResponse)
async def import_from_arxiv(
    kb_id: str,
    request: KBImportArxiv,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from arXiv.

    Per D-08: Paper inherits KB config. Request contains only arxivId field.
    Processing uses KB's stored embedding_model, parse_engine, etc.
    """
    # Stub - will fetch KB and use kb config for processing
    return KBResponse(
        success=True,
        data={
            "message": "Import arXiv endpoint - to be implemented",
            "arxivId": request.arxivId,
        },
    )


@router.post("/{kb_id}/batch-upload", response_model=KBResponse)
async def batch_upload_to_kb(
    kb_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Batch upload PDFs to a knowledge base.

    Per D-08: All papers inherit KB config. No config fields in request.
    """
    # Stub - will fetch KB and use kb config for all paper processing
    return KBResponse(
        success=True,
        data={"message": "Batch upload endpoint - to be implemented", "kbId": kb_id},
    )


# =============================================================================
# KB Search & Query - Real implementations using existing services
# =============================================================================


class KBQueryRequest(BaseModel):
    """Request for KB Q&A."""

    query: str = Field(..., min_length=1)
    topK: int = Field(default=10, ge=1, le=50)


class KBQueryResponse(BaseModel):
    """Response for KB Q&A."""

    answer: str
    citations: Optional[List[dict]] = None
    sources: Optional[List[dict]] = None
    confidence: float = 0.0


@router.post("/{kb_id}/query", response_model=KBResponse)
async def kb_query(
    kb_id: str,
    request: KBQueryRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Knowledge base Q&A - uses existing RAG service with KB paper filter.

    Per B-02: Real implementation replacing stub.
    Uses MultimodalSearchService for retrieval + ZhipuLLM for generation.
    """
    try:
        # Verify KB ownership and get papers
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Get papers in this KB
        paper_ids_result = await db.execute(
            select(Paper.id).where(
                Paper.knowledge_base_id == kb_id, Paper.user_id == user_id
            )
        )
        paper_ids = [row[0] for row in paper_ids_result.fetchall()]

        if not paper_ids:
            return KBResponse(
                success=True,
                data={
                    "answer": "知识库暂无论文，请先导入论文后再进行问答。",
                    "citations": [],
                    "sources": [],
                    "confidence": 0.0,
                },
            )

        # Use existing MultimodalSearchService (per D-15)
        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()

        # Execute search with KB paper filter
        result = await service.search(
            query=request.query,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=request.topK,
            use_reranker=True,
        )

        # Build context from top results
        context_chunks = result.get("results", [])[:5]
        context_text = "\n\n---\n\n".join(
            [
                f"[{i + 1}] {chunk.get('content_data', '')}"
                for i, chunk in enumerate(context_chunks)
            ]
        )

        # Use ZhipuAI for answer generation
        from app.utils.zhipu_client import ZhipuLLMClient

        llm_client = ZhipuLLMClient()

        system_prompt = """You are a helpful research assistant. Answer the user's question based on the provided context from academic papers in the knowledge base.

Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite relevant parts using [1], [2], etc.
3. If the context doesn't contain enough information, say so
4. Keep the answer concise but comprehensive
5. Use markdown formatting for better readability"""

        user_message = f"""Context from papers in knowledge base '{kb.name}':
{context_text}

Question: {request.query}

Please provide a comprehensive answer based on the context above."""

        llm_response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )

        # Extract answer
        if hasattr(llm_response, "choices") and llm_response.choices:
            answer = llm_response.choices[0].message.content
        else:
            answer = "无法生成回答"

        # Format citations/sources
        title_result = await db.execute(
            select(Paper.id, Paper.title).where(Paper.id.in_(paper_ids))
        )
        paper_titles = {row[0]: row[1] for row in title_result.fetchall()}

        citations = []
        for res in result.get("results", [])[:5]:
            paper_id = res.get("paper_id")
            citations.append(
                {
                    "paper_id": paper_id,
                    "paperId": paper_id,
                    "paperTitle": paper_titles.get(paper_id),
                    "chunk_id": res.get("id"),
                    "content_preview": res.get("content_data", "")[:200],
                    "score": res.get("score", 0.0),
                    "page": res.get("page_num"),
                    "content_type": res.get("content_type"),
                }
            )

        # Calculate confidence
        confidence = 0.0
        if citations:
            confidence = min(
                sum(c.get("score", 0.0) for c in citations[:3]) / len(citations[:3]),
                1.0,
            )

        logger.info("KB query executed", kb_id=kb_id, query=request.query[:50])

        return KBResponse(
            success=True,
            data={
                "answer": answer,
                "citations": citations,
                "sources": citations,
                "confidence": confidence,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("KB query error", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"KB query failed: {str(e)}"),
        )


@router.get("/{kb_id}/upload-history", response_model=KBResponse)
async def get_kb_upload_history(
    kb_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get upload history records related to papers in a specific KB."""
    try:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        records_result = await db.execute(
            select(
                UploadHistory,
                Paper.title.label("paper_title"),
                ProcessingTask.status.label("processing_status"),
                ProcessingTask.error_message.label("task_error"),
                ProcessingTask.updated_at.label("task_updated_at"),
                ProcessingTask.completed_at.label("task_completed_at"),
            )
            .join(Paper, UploadHistory.paper_id == Paper.id)
            .outerjoin(ProcessingTask, ProcessingTask.paper_id == Paper.id)
            .where(
                UploadHistory.user_id == user_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
            .order_by(UploadHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = records_result.all()

        total_result = await db.execute(
            select(func.count(UploadHistory.id))
            .select_from(UploadHistory)
            .join(Paper, UploadHistory.paper_id == Paper.id)
            .where(
                UploadHistory.user_id == user_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
        )
        total = total_result.scalar() or 0

        formatted_records = []
        for row in records:
            upload_hist = row[0]
            processing_status = row.processing_status or upload_hist.status.lower()
            display_status = upload_hist.status
            if row.processing_status:
                normalized = str(row.processing_status).lower()
                if normalized == "completed":
                    display_status = "COMPLETED"
                elif normalized == "failed":
                    display_status = "FAILED"
                else:
                    display_status = "PROCESSING"

            progress = 100 if display_status == "COMPLETED" else 0
            if display_status == "PROCESSING":
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
                progress = progress_map.get(processing_status, 50)

            formatted_records.append(
                {
                    "id": upload_hist.id,
                    "userId": upload_hist.user_id,
                    "paperId": upload_hist.paper_id,
                    "filename": upload_hist.filename,
                    "status": display_status,
                    "chunksCount": upload_hist.chunks_count,
                    "llmTokens": upload_hist.llm_tokens,
                    "pageCount": upload_hist.page_count,
                    "imageCount": upload_hist.image_count,
                    "tableCount": upload_hist.table_count,
                    "errorMessage": upload_hist.error_message or row.task_error,
                    "processingTime": upload_hist.processing_time,
                    "createdAt": upload_hist.created_at.isoformat()
                    if upload_hist.created_at
                    else None,
                    "updatedAt": (
                        row.task_updated_at.isoformat()
                        if row.task_updated_at
                        else (
                            upload_hist.updated_at.isoformat()
                            if upload_hist.updated_at
                            else None
                        )
                    ),
                    "completedAt": row.task_completed_at.isoformat()
                    if row.task_completed_at
                    else None,
                    "processingStatus": processing_status,
                    "progress": progress,
                    "paper": (
                        {
                            "id": upload_hist.paper_id,
                            "title": row.paper_title or upload_hist.filename,
                            "filename": upload_hist.filename,
                        }
                        if upload_hist.paper_id
                        else None
                    ),
                }
            )

        return KBResponse(
            success=True,
            data={
                "records": formatted_records,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get KB upload history", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get KB upload history: {str(e)}"),
        )


@router.post("/{kb_id}/search", response_model=KBResponse)
async def kb_vector_search(
    kb_id: str,
    request: KBSearch,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Vector search within a knowledge base - real implementation.

    Per B-02: Real implementation using MultimodalSearchService.
    Returns top-K chunks matching query, filtered by KB papers.
    """
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Get papers in this KB
        paper_ids_result = await db.execute(
            select(Paper.id).where(
                Paper.knowledge_base_id == kb_id, Paper.user_id == user_id
            )
        )
        paper_ids = [row[0] for row in paper_ids_result.fetchall()]

        if not paper_ids:
            return KBResponse(
                success=True,
                data={"results": [], "total": 0, "query": request.query},
            )

        # Use existing MultimodalSearchService
        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()

        # Execute search
        result = await service.search(
            query=request.query,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=request.topK,
            use_reranker=True,
        )

        # Format results for KB response
        title_result = await db.execute(
            select(Paper.id, Paper.title).where(Paper.id.in_(paper_ids))
        )
        paper_titles = {row[0]: row[1] for row in title_result.fetchall()}

        results = []
        for res in result.get("results", []):
            paper_id = res.get("paper_id")
            results.append(
                {
                    "id": res.get("id"),
                    "paperId": paper_id,
                    "paperTitle": paper_titles.get(paper_id),
                    "content": res.get("content_data", ""),
                    "section": res.get("section"),
                    "page": res.get("page_num"),
                    "score": res.get("score", 0.0),
                    "contentType": res.get("content_type"),
                }
            )

        logger.info(
            "KB vector search executed",
            kb_id=kb_id,
            query=request.query[:50],
            results_count=len(results),
        )

        return KBResponse(
            success=True,
            data={"results": results, "total": len(results), "query": request.query},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("KB search error", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"KB search failed: {str(e)}"),
        )


__all__ = ["router"]
