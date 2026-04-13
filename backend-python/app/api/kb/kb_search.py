"""KB Search operations - List papers, vector search, upload history.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- GET /api/v1/knowledge-bases/{kb_id}/papers - List KB papers
- POST /api/v1/knowledge-bases/{kb_id}/search - KB vector search
- GET /api/v1/knowledge-bases/{kb_id}/upload-history - Upload history
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper, PaperChunk
from app.models.task import ProcessingTask
from app.models.upload_history import UploadHistory
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBSearch(BaseModel):
    """Request for KB vector search."""

    query: str
    topK: int = Field(default=10, ge=1, le=50)


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

        query = (
            select(Paper)
            .where(Paper.knowledge_base_id == kb_id, Paper.user_id == user_id)
            .order_by(desc(Paper.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(query)
        papers = result.scalars().all()

        total_result = await db.execute(
            select(func.count(Paper.id)).where(
                Paper.knowledge_base_id == kb_id, Paper.user_id == user_id
            )
        )
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


@router.post("/{kb_id}/search", response_model=KBResponse)
async def kb_vector_search(
    kb_id: str,
    request: KBSearch,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Vector search within a knowledge base.

    Per B-02: Real implementation using MultimodalSearchService.
    Returns top-K chunks matching query, filtered by KB papers.
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

        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()
        result = await service.search(
            query=request.query,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=request.topK,
            use_reranker=True,
        )

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
                progress = progress_map.get(processing_status, 0)

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


__all__ = ["router"]
