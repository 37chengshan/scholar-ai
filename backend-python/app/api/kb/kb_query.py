"""KB Query operations - RAG Q&A with citations.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- POST /api/v1/knowledge-bases/{kb_id}/query - KB RAG Q&A
"""

from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBQueryRequest(BaseModel):
    """Request for KB Q&A."""

    query: str = Field(..., min_length=1)
    topK: int = Field(default=10, ge=1, le=50)


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
                f"[{i + 1}] {chunk.get('content_data', '')}"
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
                    "content_preview": res.get("content_data", "")[:200],
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
