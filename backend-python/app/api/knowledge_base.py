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

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
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
                "knowledgeBases": [_format_kb_response(kb) for kb in kbs],
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

        return KBResponse(success=True, data=_format_kb_response(kb))

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

        return KBResponse(success=True, data=_format_kb_response(kb))

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

        return KBResponse(success=True, data=_format_kb_response(kb))

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

        return KBResponse(
            success=True,
            data={
                "papers": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "authors": p.authors,
                        "year": p.year,
                        "status": p.status,
                        "createdAt": p.created_at.isoformat() if p.created_at else None,
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
    # Stub - will fetch KB and use kb.embedding_model, kb.parse_engine, etc. for processing
    return KBResponse(
        success=True,
        data={"message": "Upload endpoint - to be implemented", "kbId": kb_id},
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
# KB Search & Chat (Stub implementations)
# =============================================================================


@router.post("/{kb_id}/search", response_model=KBResponse)
async def kb_vector_search(
    kb_id: str,
    request: KBSearch,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Vector search within a knowledge base (stub - will use Milvus)."""
    # Stub - will be implemented in future
    return KBResponse(
        success=True,
        data={
            "message": "KB search endpoint - to be implemented",
            "query": request.query,
        },
    )


@router.post("/{kb_id}/chat/stream")
async def kb_chat_stream(
    kb_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming for agentic Q&A within KB (stub - will use existing chat logic)."""
    # Stub - will be implemented in future
    return {
        "success": True,
        "data": {"message": "KB chat stream endpoint - to be implemented"},
    }


__all__ = ["router"]
