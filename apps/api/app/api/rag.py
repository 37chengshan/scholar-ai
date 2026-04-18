"""RAG问答路由 - Interactive Q&A with Streaming and Conversation Support

Provides endpoints for:
- Blocking RAG queries with caching
- Streaming RAG queries via SSE
- Conversation session management
- Unified multimodal search with query understanding
"""

import time
import uuid
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.utils.logger import logger
from app.utils.problem_detail import Errors
from app.utils.cache import (
    get_cached_response,
    set_cached_response,
)
from app.utils.session_manager import session_manager
from app.models.session import SessionUpdate
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.streaming import (
    stream_rag_response,
    format_sse_done,
    format_sse_event,
)
from app.core.multimodal_search_service import get_multimodal_search_service
from app.deps import CurrentUserId

router = APIRouter()


def _source_score(source: Dict) -> float:
    """Read source score from unified field, with legacy fallback."""
    score = source.get("score")
    if score is None:
        score = source.get("similarity", 0.0)
    try:
        return max(0.0, min(float(score), 1.0))
    except (TypeError, ValueError):
        return 0.0


def normalize_source_contract(source: Dict) -> Dict:
    """Normalize source payload to canonical retrieval contract.

    Canonical fields:
    - score
    - page_num
    - text_preview

    Legacy aliases are preserved when already present to avoid client regressions.
    """
    normalized = dict(source)
    normalized["score"] = _source_score(source)

    page_num = source.get("page_num")
    if page_num is None:
        page_num = source.get("page")
    normalized["page_num"] = page_num

    if normalized.get("text_preview") is None:
        normalized["text_preview"] = (
            source.get("content_preview")
            or source.get("snippet")
            or source.get("content")
            or ""
        )

    return normalized


def calculate_confidence(answer: str, sources: List[dict]) -> float:
    """Calculate confidence from coverage, diversity, and support strength.

    Confidence dimensions:
    - score coverage: average top source relevance
    - evidence diversity: distinct paper/section support
    - answer support: source volume and answer substance
    """
    if not sources:
        return 0.0

    normalized_sources = [normalize_source_contract(source) for source in sources]
    ranked_sources = sorted(normalized_sources, key=_source_score, reverse=True)
    top_sources = ranked_sources[:5]

    # 1) Score coverage (dominant signal)
    top_scores = [_source_score(source) for source in top_sources]
    score_coverage = sum(top_scores) / len(top_scores) if top_scores else 0.0

    # 2) Evidence diversity across papers/sections/pages
    diversity_keys = set()
    for source in top_sources:
        paper_id = source.get("paper_id") or "unknown"
        section = source.get("section")
        page_num = source.get("page_num")
        location = section or (f"page:{page_num}" if page_num is not None else "unknown")
        diversity_keys.add((paper_id, location))

    evidence_diversity = min(len(diversity_keys) / max(len(top_sources), 1), 1.0)

    # 3) Answer support strength (source count + answer length)
    source_support = min(len(sources) / 5, 1.0)
    answer_length_support = min(len((answer or "").split()) / 120, 1.0)
    answer_support = 0.6 * source_support + 0.4 * answer_length_support

    confidence = (
        0.55 * score_coverage
        + 0.25 * evidence_diversity
        + 0.20 * answer_support
    )
    return round(min(confidence, 1.0), 4)


# =============================================================================
# Request/Response Models
# =============================================================================

class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    paper_ids: Optional[List[str]] = Field(None, description="要查询的论文ID列表")
    query_type: str = Field("single", description="查询类型: single, cross_paper, evolution")
    top_k: int = Field(10, ge=1, le=50, description="返回的chunk数量")
    conversation_id: Optional[str] = Field(None, description="对话会话ID (多轮对话)")


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    answer: str = Field(..., description="回答内容")
    query: Optional[str] = Field(None, description="原始查询")
    expanded_query: Optional[str] = Field(None, description="扩展后的查询")
    intent: Optional[str] = Field(None, description="查询意图 (question/compare/summary/evolution)")
    metadata_filters: Optional[Dict] = Field(None, description="提取的元数据过滤条件")
    sources: List[dict] = Field(..., description="引用来源")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    conversation_id: Optional[str] = Field(None, description="对话会话ID")
    cached: bool = Field(False, description="是否来自缓存")


class ConversationSessionResponse(BaseModel):
    """对话会话响应"""
    session_id: str
    messages: List[dict]
    paper_ids: List[str]
    created_at: str
    updated_at: str
    message_count: int


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    sessions: List[dict]
    total: int


class AgenticSearchRequest(BaseModel):
    """Agentic search request for complex cross-paper queries."""
    query: str = Field(..., min_length=1, description="User query")
    query_type: str = Field("single", description="Query type: single, cross_paper, evolution")
    paper_ids: Optional[List[str]] = Field(None, description="Paper IDs to search")
    max_rounds: int = Field(3, ge=1, le=5, description="Maximum retrieval rounds")
    top_k: int = Field(5, ge=1, le=20, description="Chunks per sub-question")


class AgenticSearchResponse(BaseModel):
    """Agentic search response with synthesized answer."""
    answer: str = Field(..., description="Synthesized answer")
    sub_questions: List[dict] = Field(..., description="Sub-questions generated")
    sources: List[dict] = Field(..., description="Citations from all sub-questions")
    rounds_executed: int = Field(..., description="Number of retrieval rounds")
    converged: bool = Field(..., description="Whether convergence was reached")
    metadata: dict = Field(default_factory=dict, description="Query metadata")


# =============================================================================
# Blocking Query Endpoint
# =============================================================================

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    user_id: str = CurrentUserId
):
    """
    RAG问答 (阻塞式)

    - 基于论文内容进行问答
    - 支持引用溯源（使用 [Paper Title, Section] 格式）
    - 支持跨文档查询
    - 1小时缓存相同查询
    - 支持多轮对话 (通过conversation_id)
    - 使用 AgenticRetrievalOrchestrator 进行引用格式化处理
    """
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    try:
        logger.info(
            "run_started",
            event_type="run_started",
            run_id=run_id,
            route="/api/v1/rag/query",
            query_type=request.query_type,
            user_id=user_id,
        )
        logger.info(f"RAG query: {request.question}, type: {request.query_type}, user: {user_id}")

        # Check cache first (with user_id and version per D-04)
        paper_ids = request.paper_ids or []
        cached = await get_cached_response(
            user_id=user_id,
            query=request.question,
            paper_ids=paper_ids,
            query_type=request.query_type,
            retrieval_version="v2",
            index_version="v1"
        )

        if cached:
            logger.info(f"Returning cached response for query: {request.question[:50]}...")
            cached_sources = [
                normalize_source_contract(source)
                for source in cached.get("sources", [])
            ]
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "run_completed",
                event_type="run_completed",
                run_id=run_id,
                route="/api/v1/rag/query",
                status="cached",
                duration_ms=round(duration_ms, 2),
            )
            return RAGQueryResponse(
                answer=cached.get("answer", ""),
                query=request.question,
                sources=cached_sources,
                confidence=cached.get("confidence", 0.0),
                conversation_id=request.conversation_id,
                cached=True
            )

        # Use AgenticRetrievalOrchestrator for proper citation formatting
        orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)

        retrieve_started = time.perf_counter()

        result = await orchestrator.retrieve(
            query=request.question,
            query_type=request.query_type,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k_per_subquestion=request.top_k,
        )

        # Extract answer and sources from orchestrator result
        answer = result.get("answer", "")
        sources = [normalize_source_contract(source) for source in result.get("sources", [])]
        retrieve_duration_ms = (time.perf_counter() - retrieve_started) * 1000

        confidence = calculate_confidence(answer, sources)

        # Build response (expanded_query/intent not available from orchestrator)
        response = RAGQueryResponse(
            answer=answer,
            query=request.question,
            expanded_query=None,  # Not available from AgenticRetrievalOrchestrator
            intent=request.query_type,  # Use query_type as intent
            metadata_filters=None,  # Not available from AgenticRetrievalOrchestrator
            sources=sources,
            confidence=confidence,
            conversation_id=request.conversation_id,
            cached=False
        )

        # Cache the response (with user_id and version per D-04)
        await set_cached_response(
            user_id=user_id,
            query=request.question,
            paper_ids=paper_ids,
            response={
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            },
            query_type=request.query_type,
            retrieval_version="v2",
            index_version="v1"
        )

        # Update conversation if conversation_id provided (with user_id per D-05)
        if request.conversation_id:
            try:
                await _update_conversation(request, answer, sources, user_id)
            except Exception as conv_err:
                logger.warning(
                    "Conversation update failed, continue returning answer",
                    run_id=run_id,
                    conversation_id=request.conversation_id,
                    error=str(conv_err),
                )

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "run_completed",
            event_type="run_completed",
            run_id=run_id,
            route="/api/v1/rag/query",
            status="success",
            duration_ms=round(duration_ms, 2),
            rag_retrieve_duration_ms=round(retrieve_duration_ms, 2),
            source_count=len(sources),
            confidence=confidence,
        )

        return response

    except Exception as e:
        logger.error(f"RAG query error: {e}")
        logger.error(
            "run_failed",
            event_type="run_failed",
            run_id=run_id,
            route="/api/v1/rag/query",
            error=str(e),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal("查询失败")
        )


# =============================================================================
# Streaming Query Endpoint
# =============================================================================

@router.post("/stream")
async def rag_query_stream(
    request: RAGQueryRequest,
    user_id: str = CurrentUserId
):
    """
    流式RAG问答 (SSE)

    - 使用Server-Sent Events实时返回token
    - 支持引用溯源
    - 支持多轮对话
    - Event格式: data: {"type": "token", "content": "..."}
    - 结束标记: data: [DONE]
    """
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    try:
        logger.info(
            "stream_started",
            event_type="stream_started",
            run_id=run_id,
            route="/api/v1/rag/stream",
            query_type=request.query_type,
            user_id=user_id,
        )
        logger.info(f"RAG stream query: {request.question}, user: {user_id}")

        paper_ids = request.paper_ids or []

        # Check cache for instant response (with user_id and version per D-04)
        cached = await get_cached_response(
            user_id=user_id,
            query=request.question,
            paper_ids=paper_ids,
            query_type=request.query_type,
            retrieval_version="v2",
            index_version="v1"
        )

        if cached:
            # Stream cached response
            logger.info(f"Streaming cached response")
            logger.info(
                "stream_completed",
                event_type="stream_completed",
                run_id=run_id,
                route="/api/v1/rag/stream",
                status="cached",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            cached_answer = cached.get("answer", "")
            cached_citations = [
                normalize_source_contract(source)
                for source in cached.get("sources", [])
            ]

            async def stream_cached():
                # Stream answer as tokens
                words = cached_answer.split()
                for word in words:
                    yield format_sse_event({"type": "token", "content": f"{word} "})

                # Send citations
                if cached_citations:
                    yield format_sse_event({"type": "citations", "content": cached_citations})

                # Send done marker
                yield format_sse_done()

            return StreamingResponse(
                stream_cached(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        # Use streaming handler for non-cached queries
        logger.info(
            "rag_answer_started",
            event_type="rag_answer_started",
            run_id=run_id,
            route="/api/v1/rag/stream",
        )
        return await stream_rag_response(
            query=request.question,
            paper_ids=paper_ids,
            conversation_id=request.conversation_id,
            query_type=request.query_type,
            top_k=request.top_k,
            user_id=user_id,
        )

    except Exception as e:
        logger.error(f"RAG stream error: {e}")
        logger.error(
            "stream_failed",
            event_type="stream_failed",
            run_id=run_id,
            route="/api/v1/rag/stream",
            error=str(e),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        # Return error as SSE event
        async def error_stream():
            yield format_sse_event({"type": "error", "content": "流式问答失败，请稍后重试"})
            yield format_sse_done()

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=status.HTTP_200_OK
        )


# =============================================================================
# Conversation Session Endpoints
# =============================================================================

@router.post("/session", response_model=ConversationSessionResponse)
async def create_conversation_session(
    paper_ids: Optional[List[str]] = None,
    user_id: str = CurrentUserId
):
    """
    创建新的对话会话

    - 使用 SessionManager 创建会话并绑定用户所有权
    - 关联论文列表
    - 支持多轮对话上下文保持
    """
    try:
        # Use SessionManager instead of direct Redis operations per D-05
        title = f"RAG Session ({len(paper_ids or [])} papers)"
        session = await session_manager.create_session(
            user_id=user_id,
            title=title
        )

        # Store paper_ids in metadata if provided
        if paper_ids:
            await session_manager.update_session(
                session_id=session.id,
                updates=SessionUpdate(metadata={"paper_ids": paper_ids})
            )

        logger.info(f"Created conversation session: {session.id} for user: {user_id}")

        return ConversationSessionResponse(
            session_id=session.id,
            messages=[],  # SessionManager doesn't store messages in session object
            paper_ids=paper_ids or [],
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=session.message_count
        )

    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal("创建会话失败")
        )


@router.get("/session/{session_id}", response_model=ConversationSessionResponse)
async def get_conversation(
    session_id: str,
    user_id: str = CurrentUserId
):
    """
    获取对话会话详情

    - 返回完整对话历史
    - 包含关联论文列表
    - 验证会话所有权 (session.user_id == current_user_id)
    """
    try:
        # Use SessionManager per D-05
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"会话不存在: {session_id}")
            )

        # Ownership check per D-05
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden("Session access denied - not owned by current user")
            )

        # Get paper_ids from metadata
        metadata = session.metadata or {}
        paper_ids = metadata.get("paper_ids", [])

        return ConversationSessionResponse(
            session_id=session.id,
            messages=[],  # Messages stored separately, not in session object
            paper_ids=paper_ids,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=session.message_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal("获取会话失败")
        )


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    session_id: str,
    user_id: str = CurrentUserId
):
    """
    删除对话会话

    - 验证所有权后从 PostgreSQL 和 Redis 删除
    - 不可恢复
    """
    try:
        # Get session first to verify ownership per D-05
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"会话不存在: {session_id}")
            )

        # Ownership check per D-05
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden("Session deletion denied - not owned by current user")
            )

        # Delete using SessionManager
        success = await session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=Errors.internal(f"删除会话失败")
            )

        logger.info(f"Deleted conversation session: {session_id} by user: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal("删除会话失败")
        )


# =============================================================================
# Agentic Search Endpoint
# =============================================================================

@router.post("/agentic", response_model=AgenticSearchResponse)
async def agentic_search(
    request: AgenticSearchRequest,
    user_id: str = CurrentUserId
):
    """
    Agentic search for complex cross-paper queries.

    - Decomposes complex queries into 3-5 sub-questions
    - Executes sub-questions in parallel via asyncio.gather
    - Multi-round retrieval (max 3 rounds) with convergence detection
    - LLM synthesis of results into coherent answer
    - Returns synthesized answer with all sub-question sources

    Query types:
    - single: Direct query (no decomposition)
    - cross_paper: Compare/contrast multiple papers
    - evolution: Track changes across paper versions (e.g., "YOLO evolution")
    """
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    try:
        logger.info(
            "run_started",
            event_type="run_started",
            run_id=run_id,
            route="/api/v1/rag/agentic",
            query_type=request.query_type,
            user_id=user_id,
        )
        logger.info(
            f"Agentic search: {request.query}, type: {request.query_type}, user: {user_id}"
        )

        # Initialize orchestrator
        orchestrator = AgenticRetrievalOrchestrator(
            max_rounds=request.max_rounds,
        )

        # Execute agentic retrieval using Milvus (per D-35)
        result = await orchestrator.retrieve(
            query=request.query,
            query_type=request.query_type,
            paper_ids=request.paper_ids or [],
            user_id=user_id,  # Use authenticated user_id
            top_k_per_subquestion=request.top_k,
        )

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "run_completed",
            event_type="run_completed",
            run_id=run_id,
            route="/api/v1/rag/agentic",
            duration_ms=round(duration_ms, 2),
            rounds_executed=result.get("rounds_executed"),
            source_count=len(result.get("sources", [])),
            converged=result.get("converged"),
        )

        return AgenticSearchResponse(
            answer=result["answer"],
            sub_questions=result["sub_questions"],
            sources=result["sources"],
            rounds_executed=result["rounds_executed"],
            converged=result["converged"],
            metadata=result.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"Agentic search error: {e}")
        logger.error(
            "run_failed",
            event_type="run_failed",
            run_id=run_id,
            route="/api/v1/rag/agentic",
            error=str(e),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal("Agentic search failed")
        )


# =============================================================================
# Helper Functions
# =============================================================================

async def _update_conversation(
    request: RAGQueryRequest,
    answer: str,
    sources: List[dict],
    user_id: str
):
    """
    Update conversation session with strict ownership.

    Per D-05: Never create ghost sessions - session must exist first.

    Args:
        request: The RAG query request
        answer: Assistant's answer
        sources: Citation sources
        user_id: User UUID for ownership verification
    """
    if not request.conversation_id:
        return

    # Get existing session from SessionManager
    session = await session_manager.get_session(request.conversation_id)

    # Per D-05: Session must exist and belong to user
    if not session:
        logger.warning(
            f"Session {request.conversation_id} not found - refusing to create ghost session"
        )
        return  # Don't auto-create ghost sessions

    if session.user_id != user_id:
        logger.warning(
            f"Session {request.conversation_id} ownership mismatch - user {user_id} cannot access"
        )
        return  # Security: don't update sessions owned by other users

    # Update metadata with new exchange
    from datetime import datetime

    metadata = session.metadata or {}
    messages = metadata.get("messages", [])

    now = datetime.utcnow().isoformat()

    # Add messages
    messages.append({"role": "user", "content": request.question, "timestamp": now})
    messages.append({
        "role": "assistant",
        "content": answer,
        "citations": sources,
        "timestamp": now
    })

    # Keep last 20 messages
    if len(messages) > 20:
        messages = messages[-20:]

    # Update paper_ids if new ones added
    if request.paper_ids:
        existing_ids = metadata.get("paper_ids", [])
        metadata["paper_ids"] = list(set(existing_ids + request.paper_ids))

    metadata["messages"] = messages

    await session_manager.update_session(
        session_id=request.conversation_id,
        updates=SessionUpdate(metadata=metadata)
    )
