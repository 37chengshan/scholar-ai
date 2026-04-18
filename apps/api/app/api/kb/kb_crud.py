"""KB CRUD operations - Create, Read, Update, Delete Knowledge Bases.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- GET /api/v1/knowledge-bases - List KBs with search/filter
- POST /api/v1/knowledge-bases - Create KB
- GET /api/v1/knowledge-bases/{kb_id} - Get KB details
- PATCH /api/v1/knowledge-bases/{kb_id} - Update KB
- DELETE /api/v1/knowledge-bases/{kb_id} - Delete KB
- POST /api/v1/knowledge-bases/batch-delete - Batch delete
- POST /api/v1/knowledge-bases/batch-export - Batch export
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors
from app.utils.logger import logger


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


class KBBatchDelete(BaseModel):
    """Request to batch delete KBs."""

    ids: List[str]


class KBBatchExport(BaseModel):
    """Request to batch export KBs."""

    ids: List[str]


class KBStorageStats(BaseModel):
    """Response for KB storage statistics."""

    success: bool = True
    data: Dict[str, Any]


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
    from app.models.paper import Paper, PaperChunk

    def _normalize_timestamp(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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

    effective_updated_at = _normalize_timestamp(kb.updated_at)
    latest_paper_update = _normalize_timestamp(latest_paper_update)
    if latest_paper_update and (
        effective_updated_at is None or latest_paper_update > effective_updated_at
    ):
        effective_updated_at = latest_paper_update

    payload["updatedAt"] = (
        effective_updated_at.isoformat() if effective_updated_at else None
    )
    return payload


# =============================================================================
# KB CRUD Endpoints - STATIC ROUTES FIRST (before /{kb_id})
# =============================================================================


@router.get("/", response_model=KBListResponse)
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


@router.post("/", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
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


# =============================================================================
# KB Batch Operations (STATIC ROUTES - before /{kb_id})
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
# KB Storage Statistics (STATIC ROUTE - before /{kb_id})
# =============================================================================


@router.get("/storage-stats", response_model=KBStorageStats)
async def get_kb_storage_stats(
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get storage statistics for user's knowledge bases.

    Returns aggregate counts and estimated storage usage.
    """
    try:
        from app.models.paper import Paper, PaperChunk

        # Count user's knowledge bases
        kb_count_result = await db.execute(
            select(func.count(KnowledgeBase.id)).where(
                KnowledgeBase.user_id == user_id
            )
        )
        kb_count = kb_count_result.scalar() or 0

        # Get KB IDs for this user
        kb_ids_result = await db.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.user_id == user_id)
        )
        kb_ids = [row[0] for row in kb_ids_result.all()]

        # Count papers in user's KBs
        paper_count_result = await db.execute(
            select(func.count(Paper.id)).where(
                Paper.knowledge_base_id.in_(kb_ids) if kb_ids else False
            )
        )
        paper_count = paper_count_result.scalar() or 0

        # Count chunks in user's KBs
        chunk_count_result = await db.execute(
            select(func.count(PaperChunk.id))
            .select_from(PaperChunk)
            .join(Paper, PaperChunk.paper_id == Paper.id)
            .where(Paper.knowledge_base_id.in_(kb_ids) if kb_ids else False)
        )
        chunk_count = chunk_count_result.scalar() or 0

        # Estimate file storage (2MB average per paper)
        avg_file_size = 2 * 1024 * 1024  # 2MB
        estimated_storage_bytes = paper_count * avg_file_size
        estimated_storage_mb = round(estimated_storage_bytes / (1024 * 1024), 1)

        return KBStorageStats(
            success=True,
            data={
                "kbCount": int(kb_count),
                "paperCount": int(paper_count),
                "chunkCount": int(chunk_count),
                "estimatedStorageMB": estimated_storage_mb,
                "storageLimitMB": 50000,  # 50GB limit
            },
        )

    except Exception as e:
        logger.error("Failed to get KB storage stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get storage stats: {str(e)}"),
        )


# =============================================================================
# KB Dynamic Routes (/{kb_id}) - AFTER all static routes
# =============================================================================


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


__all__ = ["router"]
