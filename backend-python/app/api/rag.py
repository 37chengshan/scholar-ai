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
    get_conversation_session,
    save_conversation_session,
    delete_conversation_session
)
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.streaming import (
    stream_rag_response,
    create_streaming_response,
    mock_token_generator
)
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.auth import CurrentUserId

router = APIRouter()


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
    - 支持引用溯源
    - 支持跨文档查询
    - 1小时缓存相同查询
    - 支持多轮对话 (通过conversation_id)
    - 使用统一MultimodalSearchService with query understanding
    """
    try:
        logger.info(f"RAG query: {request.question}, type: {request.query_type}, user: {user_id}")

        # Check cache first
        paper_ids = request.paper_ids or []
        cached = await get_cached_response(
            request.question,
            paper_ids,
            request.query_type
        )

        if cached:
            logger.info(f"Returning cached response for query: {request.question[:50]}...")
            return RAGQueryResponse(
                answer=cached.get("answer", ""),
                query=request.question,
                sources=cached.get("sources", []),
                confidence=cached.get("confidence", 0.0),
                conversation_id=request.conversation_id,
                cached=True
            )

        # Use unified MultimodalSearchService (per D-15)
        service = get_multimodal_search_service()

        # Execute multimodal search with query understanding
        result = await service.search(
            query=request.question,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=request.top_k,
            use_reranker=True,
        )

        # Build answer using LLM with retrieved context
        context_chunks = result.get("results", [])[:5]  # Top 5 chunks
        context_text = "\n\n---\n\n".join([
            f"[{i+1}] {chunk.get('content_data', '')}" 
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Use ZhipuAI to generate answer
        from app.utils.zhipu_client import ZhipuLLMClient
        llm_client = ZhipuLLMClient()
        
        system_prompt = """You are a helpful research assistant. Answer the user's question based on the provided context from academic papers.
        
Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite relevant parts using [1], [2], etc.
3. If the context doesn't contain enough information, say so
4. Keep the answer concise but comprehensive
5. Use markdown formatting for better readability"""

        user_message = f"""Context from papers:
{context_text}

Question: {request.question}

Please provide a comprehensive answer based on the context above."""

        llm_response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1024,
            temperature=0.7
        )
        
        # Extract answer from ZhipuAI response
        if hasattr(llm_response, 'choices') and llm_response.choices:
            answer = llm_response.choices[0].message.content
        else:
            answer = "Unable to generate answer"

        # Format sources from results
        sources = []
        for res in result.get("results", [])[:5]:  # Top 5 sources
            sources.append({
                "paper_id": res.get("paper_id"),
                "chunk_id": res.get("id"),
                "content_preview": res.get("content_data", "")[:200],
                "score": res.get("score", 0.0),
                "page": res.get("page_num"),
                "content_type": res.get("content_type"),
            })

        # Calculate confidence from top results
        confidence = 0.0
        if sources:
            confidence = min(sum(s.get("score", 0.0) for s in sources[:3]) / len(sources[:3]), 1.0)

        # Build response with query understanding fields (per D-15)
        response = RAGQueryResponse(
            answer=answer,
            query=request.question,
            expanded_query=result.get("expanded_query"),
            intent=result.get("intent"),
            metadata_filters=result.get("metadata_filters"),
            sources=sources,
            confidence=confidence,
            conversation_id=request.conversation_id,
            cached=False
        )

        # Cache the response
        await set_cached_response(
            request.question,
            paper_ids,
            {
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            },
            request.query_type
        )

        # Update conversation if conversation_id provided
        if request.conversation_id:
            await _update_conversation(request, answer, sources)

        return response

    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"查询失败: {str(e)}")
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
    try:
        logger.info(f"RAG stream query: {request.question}, user: {user_id}")

        paper_ids = request.paper_ids or []

        # Check cache for instant response
        cached = await get_cached_response(
            request.question,
            paper_ids,
            request.query_type
        )

        if cached:
            # Stream cached response
            logger.info(f"Streaming cached response")
            cached_answer = cached.get("answer", "")
            cached_citations = cached.get("sources", [])

            async def stream_cached():
                import json
                # Stream answer as tokens
                words = cached_answer.split()
                for word in words:
                    yield f'data: {{"type": "token", "content": "{word} "}}\n\n'

                # Send citations
                if cached_citations:
                    yield f'data: {{"type": "citations", "content": {json.dumps(cached_citations, ensure_ascii=False)}}}\n\n'

                # Send done marker
                yield "data: [DONE]\n\n"

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
        return await stream_rag_response(
            query=request.question,
            paper_ids=paper_ids,
            conversation_id=request.conversation_id,
            query_type=request.query_type,
            top_k=request.top_k
        )

    except Exception as e:
        logger.error(f"RAG stream error: {e}")

        # Return error as SSE event
        async def error_stream():
            import json
            yield f'data: {{"type": "error", "content": "{str(e)}"}}\n\n'
            yield "data: [DONE]\n\n"

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
    paper_ids: Optional[List[str]] = None
):
    """
    创建新的对话会话

    - 生成唯一session_id
    - 关联论文列表
    - 支持多轮对话上下文保持
    """
    try:
        session_id = str(uuid.uuid4())
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        session_data = {
            "session_id": session_id,
            "messages": [],
            "paper_ids": paper_ids or [],
            "created_at": now,
            "updated_at": now
        }

        await save_conversation_session(session_id, session_data)

        logger.info(f"Created conversation session: {session_id}")

        return ConversationSessionResponse(
            session_id=session_id,
            messages=[],
            paper_ids=paper_ids or [],
            created_at=now,
            updated_at=now,
            message_count=0
        )

    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"创建会话失败: {str(e)}")
        )


@router.get("/session/{session_id}", response_model=ConversationSessionResponse)
async def get_conversation(session_id: str):
    """
    获取对话会话详情

    - 返回完整对话历史
    - 包含关联论文列表
    """
    try:
        session = await get_conversation_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"会话不存在: {session_id}")
            )

        return ConversationSessionResponse(
            session_id=session["session_id"],
            messages=session.get("messages", []),
            paper_ids=session.get("paper_ids", []),
            created_at=session.get("created_at", ""),
            updated_at=session.get("updated_at", ""),
            message_count=len(session.get("messages", []))
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"获取会话失败: {str(e)}")
        )


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(session_id: str):
    """
    删除对话会话

    - 清除Redis中的会话数据
    - 不可恢复
    """
    try:
        success = await delete_conversation_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"会话不存在: {session_id}")
            )

        logger.info(f"Deleted conversation session: {session_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"删除会话失败: {str(e)}")
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
    try:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Agentic search failed: {str(e)}")
        )


# =============================================================================
# Helper Functions
# =============================================================================

async def _update_conversation(
    request: RAGQueryRequest,
    answer: str,
    sources: List[dict]
):
    """
    Update conversation session with new exchange.

    Args:
        request: The RAG query request
        answer: Assistant's answer
        sources: Citation sources
    """
    if not request.conversation_id:
        return

    session = await get_conversation_session(request.conversation_id)

    if not session:
        # Create new session if it doesn't exist
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        session = {
            "session_id": request.conversation_id,
            "messages": [],
            "paper_ids": request.paper_ids or [],
            "created_at": now,
            "updated_at": now
        }

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Add user message
    session["messages"].append({
        "role": "user",
        "content": request.question,
        "timestamp": now
    })

    # Add assistant message
    session["messages"].append({
        "role": "assistant",
        "content": answer,
        "citations": sources,
        "timestamp": now
    })

    # Limit to last 20 messages (10 exchanges)
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]

    # Update paper_ids if changed
    if request.paper_ids:
        session["paper_ids"] = list(set(
            session.get("paper_ids", []) + request.paper_ids
        ))

    session["updated_at"] = now

    # Save session
    await save_conversation_session(request.conversation_id, session)
