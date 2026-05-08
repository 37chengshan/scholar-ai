"""KB Papers Management - List, add, remove papers from KB, and KB Q&A.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.
Per D-01: kb_papers.py contains papers management + query (内聚).

Endpoints:
- GET /api/v1/knowledge-bases/{kb_id}/papers - List KB papers
- POST /api/v1/knowledge-bases/{kb_id}/papers - Add paper to KB
- DELETE /api/v1/knowledge-bases/{kb_id}/papers/{paper_id} - Remove paper from KB
- POST /api/v1/knowledge-bases/{kb_id}/query - KB RAG Q&A
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper, PaperChunk
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


async def _resolve_representative_chunk_ids(
    db: AsyncSession,
    raw_results: List[Dict[str, Any]],
) -> Dict[tuple[str, str], str]:
    """Resolve stable paper chunk ids for legacy summary hits lacking source ids."""
    lookup: Dict[tuple[str, str], str] = {}

    def _has_canonical_chunk_id(item: Dict[str, Any]) -> bool:
        raw_data = item.get("raw_data") or {}
        if item.get("source_chunk_id") or raw_data.get("source_chunk_id"):
            return True
        if item.get("chunk_id") or raw_data.get("chunk_id"):
            return True
        if str(item.get("index_type") or "") == "summary":
            return False
        return bool(item.get("source_id"))

    pending_pairs = {
        (str(item.get("paper_id") or ""), str(item.get("section") or ""))
        for item in raw_results
        if item.get("paper_id")
        and not _has_canonical_chunk_id(item)
    }
    if not pending_pairs:
        return lookup

    paper_ids = sorted({paper_id for paper_id, _ in pending_pairs if paper_id})
    if not paper_ids:
        return lookup

    chunk_rows = await db.execute(
        select(
            PaperChunk.paper_id,
            PaperChunk.id,
            PaperChunk.section,
            PaperChunk.page_start,
        )
        .where(PaperChunk.paper_id.in_(paper_ids))
        .order_by(PaperChunk.paper_id, PaperChunk.page_start, PaperChunk.id)
    )
    by_paper: Dict[str, List[tuple[str, str, int | None]]] = {}
    for paper_id, chunk_id, section, page_start in chunk_rows.fetchall():
        by_paper.setdefault(str(paper_id), []).append(
            (str(chunk_id), str(section or "").strip().lower(), page_start)
        )

    for paper_id, section in pending_pairs:
        candidates = by_paper.get(paper_id, [])
        if not candidates:
            continue
        normalized_section = section.strip().lower()
        chosen: str | None = None
        if normalized_section and normalized_section != "_paper":
            for chunk_id, chunk_section, _ in candidates:
                if chunk_section == normalized_section:
                    chosen = chunk_id
                    break
            if chosen is None:
                for chunk_id, chunk_section, _ in candidates:
                    if normalized_section in chunk_section or chunk_section in normalized_section:
                        chosen = chunk_id
                        break
        if chosen is None:
            chosen = candidates[0][0]
        lookup[(paper_id, section)] = chosen

    return lookup


# =============================================================================
# Request/Response Models
# =============================================================================


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBPaperAdd(BaseModel):
    """Request to add paper to KB."""

    paperId: str


class KBQueryRequest(BaseModel):
    """Request for KB Q&A."""

    query: str = Field(..., min_length=1)
    topK: int = Field(default=10, ge=1, le=50)


@router.post("/{kb_id}/search", response_model=KBResponse)
async def kb_search(
    kb_id: str,
    request: KBQueryRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Search within a knowledge base and return matching evidence chunks."""
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
            return KBResponse(success=True, data={"results": [], "total": 0})

        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()
        result = await service.search(
            query=request.query,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=request.topK,
            use_reranker=True,
        )

        raw_results = result.get("results", [])
        result_paper_ids = list(
            {item.get("paper_id") for item in raw_results if item.get("paper_id")}
        )
        paper_titles: dict[str, str] = {}
        if result_paper_ids:
            title_result = await db.execute(
                select(Paper.id, Paper.title).where(Paper.id.in_(result_paper_ids))
            )
            paper_titles = {row[0]: row[1] for row in title_result.fetchall()}
        representative_chunk_ids = await _resolve_representative_chunk_ids(db, raw_results)

        mapped_results = [
            {
                "id": str(item.get("id", "")),
                "paperId": item.get("paper_id", ""),
                "paperTitle": paper_titles.get(item.get("paper_id")),
                "content": (item.get("text") or item.get("content") or "")[:500],
                "section": item.get("section"),
                "page": item.get("page_num"),
                "sourceChunkId": str(
                    item.get("source_chunk_id")
                    or (item.get("raw_data") or {}).get("source_chunk_id")
                    or (item.get("raw_data") or {}).get("chunk_id")
                    or (
                        representative_chunk_ids.get(
                            (str(item.get("paper_id") or ""), str(item.get("section") or ""))
                        )
                        if str(item.get("index_type") or "") == "summary"
                        else None
                    )
                    or item.get("source_id")
                    or representative_chunk_ids.get(
                        (str(item.get("paper_id") or ""), str(item.get("section") or ""))
                    )
                    or item.get("id", "")
                ),
                "score": item.get(
                    "score",
                    item.get("rrf_score", item.get("hybrid_score", item.get("distance", 0.0))),
                ),
            }
            for item in raw_results
        ]

        logger.info(
            "KB search executed",
            kb_id=kb_id,
            query=request.query[:50],
            result_count=len(mapped_results),
        )

        return KBResponse(
            success=True,
            data={
                "results": mapped_results,
                "total": len(mapped_results),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to search KB", error=str(e), kb_id=kb_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to search knowledge base: {str(e)}"),
        )


# =============================================================================
# KB Papers Management Endpoints
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
            select(
                Paper.id,
                Paper.title,
                Paper.authors,
                Paper.year,
                Paper.venue,
                Paper.status,
                Paper.created_at,
                Paper.updated_at,
            )
            .where(Paper.knowledge_base_id == kb_id, Paper.user_id == user_id)
            .order_by(desc(Paper.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(query)
        papers = result.all()

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


@router.post("/{kb_id}/papers", response_model=KBResponse)
async def add_paper_to_kb(
    kb_id: str,
    request: KBPaperAdd,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Add an existing paper to a knowledge base."""
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

        paper_result = await db.execute(
            select(Paper).where(Paper.id == request.paperId, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

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
# KB Query Endpoint
# =============================================================================


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
                data={
                    "answer": "知识库暂无论文，请先导入论文后再进行问答。",
                    "citations": [],
                    "sources": [],
                    "confidence": 0.0,
                },
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

        context_chunks = result.get("results", [])[:5]
        context_text = "\n\n---\n\n".join(
            [
                f"[{i + 1}] {chunk.get('text') or chunk.get('content', '')}"
                for i, chunk in enumerate(context_chunks)
            ]
        )

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

        if hasattr(llm_response, "choices") and llm_response.choices:
            answer = llm_response.choices[0].message.content
        else:
            answer = "无法生成回答"

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
                    "content_preview": (
                        res.get("text")
                        or res.get("content")
                        or ""
                    )[:200],
                    "score": res.get("score", 0.0),
                    "page": res.get("page_num"),
                    "content_type": res.get("content_type"),
                }
            )

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


__all__ = ["router"]
