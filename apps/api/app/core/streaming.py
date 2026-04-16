"""SSE streaming utilities for RAG (Retrieval-Augmented Generation) responses.

Provides FastAPI StreamingResponse generators for real-time token streaming
with proper SSE formatting and citation events.
"""

import json
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.utils.logger import logger


class StreamToken(BaseModel):
    """Single token/chunk from LLM stream."""
    type: str = "token"
    content: str


class StreamCitations(BaseModel):
    """Citations event at end of stream."""
    type: str = "citations"
    content: list[dict[str, Any]]


class StreamError(BaseModel):
    """Error event in stream."""
    type: str = "error"
    content: str


class StreamDone(BaseModel):
    """Stream completion marker."""
    type: str = "done"


def format_sse_event(data: Dict[str, Any]) -> str:
    """
    Format data as SSE event string.

    Args:
        data: Dictionary to serialize and format

    Returns:
        Formatted SSE event string with data: prefix and double newline
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def format_sse_done() -> str:
    """
    Format SSE stream completion marker.

    Returns:
        SSE done marker string
    """
    return "data: [DONE]\n\n"


async def stream_tokens(
    token_generator: AsyncGenerator[str, None],
    citations: Optional[list[dict[str, Any]]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from LLM with optional citations at end.

    Args:
        token_generator: Async generator yielding token strings
        citations: List of citation objects to send at end

    Yields:
        SSE-formatted event strings
    """
    try:
        # Stream tokens
        async for token in token_generator:
            if token:
                event = StreamToken(content=token)
                yield format_sse_event(event.model_dump())

        # Send citations if provided
        if citations:
            citation_event = StreamCitations(content=citations)
            yield format_sse_event(citation_event.model_dump())

        # Send completion marker
        yield format_sse_done()

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_event = StreamError(content=str(e))
        yield format_sse_event(error_event.model_dump())
        yield format_sse_done()


async def mock_token_generator(
    text: str,
    chunk_size: int = 5,
    delay_ms: float = 50
) -> AsyncGenerator[str, None]:
    """
    Mock token generator for testing - yields text in chunks.

    Args:
        text: Full text to stream
        chunk_size: Number of characters per chunk
        delay_ms: Delay between chunks in milliseconds (for simulation)

    Yields:
        Text chunks
    """
    import asyncio

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        yield chunk
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)


async def create_streaming_response(
    token_generator: AsyncGenerator[str, None],
    citations: Optional[list[dict[str, Any]]] = None,
    status_code: int = 200
) -> StreamingResponse:
    """
    Create a FastAPI StreamingResponse for SSE.

    Args:
        token_generator: Async generator yielding token strings
        citations: List of citation objects to send at end
        status_code: HTTP status code (default: 200)

    Returns:
        Configured StreamingResponse with text/event-stream content type
    """
    return StreamingResponse(
        stream_tokens(token_generator, citations),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
        status_code=status_code
    )


def parse_citations_from_answer(answer: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse citations from answer text.

    Looks for patterns like [1], [2], etc. and extracts them as citations.

    Args:
        answer: Answer text potentially containing citation markers

    Returns:
        Tuple of (cleaned_answer, citations_list)
    """
    import re

    # Find all citation markers [1], [2], etc.
    citation_pattern = r'\[(\d+)\]'
    citation_numbers = re.findall(citation_pattern, answer)

    # Remove citation markers from answer
    cleaned_answer = re.sub(citation_pattern, '', answer).strip()

    # Create citation objects
    citations = []
    for num in citation_numbers:
        citations.append({
            "citation_number": int(num),
            "paper_id": None,  # Will be filled by caller
            "chunk_id": None,
            "page": None,
            "score": None
        })

    return cleaned_answer, citations


class StreamingRAGHandler:
    """
    Handler for streaming RAG responses with conversation context.
    """

    def __init__(
        self,
        query: str,
        paper_ids: list[str],
        conversation_id: Optional[str] = None,
        query_type: str = "single"
    ):
        self.query = query
        self.paper_ids = paper_ids
        self.conversation_id = conversation_id
        self.query_type = query_type
        self.messages: list[dict[str, Any]] = []

    async def build_prompt_with_context(self) -> str:
        """
        Build LLM prompt including conversation history.

        Returns:
            Formatted prompt string with context
        """
        from app.utils.cache import get_conversation_session

        prompt_parts = []

        # Add system instruction
        prompt_parts.append(
            "You are a helpful research assistant. Answer the user's question "
            "based on the provided research papers. Include citations to specific "
            "sections or pages when possible."
        )

        # Add conversation context if available
        if self.conversation_id:
            session = await get_conversation_session(self.conversation_id)
            if session and "messages" in session:
                prompt_parts.append("\nPrevious conversation:")
                for msg in session["messages"][-5:]:  # Last 5 messages
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    prompt_parts.append(f"{role}: {content}")

        # Add current query
        prompt_parts.append(f"\nUser question: {self.query}")
        prompt_parts.append(
            f"\nAnswer based on the following papers: {', '.join(self.paper_ids)}"
        )

        return "\n".join(prompt_parts)

    async def stream_answer(
        self,
        answer_generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """
        Stream answer with automatic conversation history update.

        Args:
            answer_generator: Async generator yielding answer tokens

        Yields:
            SSE-formatted event strings
        """
        full_answer = []
        citations = []

        async for token in answer_generator:
            full_answer.append(token)
            yield format_sse_event(StreamToken(content=token).model_dump())

        # Parse any citations from full answer
        answer_text = "".join(full_answer)
        _, parsed_citations = parse_citations_from_answer(answer_text)

        # TODO: Map citation numbers to actual paper chunks
        # For now, return empty citations

        if citations or parsed_citations:
            yield format_sse_event(
                StreamCitations(content=citations or parsed_citations).model_dump()
            )

        # Update conversation history
        if self.conversation_id:
            await self._update_conversation(answer_text, citations)

        yield format_sse_done()

    async def _update_conversation(
        self,
        answer: str,
        citations: list[dict[str, Any]]
    ):
        """
        Update conversation session with new exchange.

        Args:
            answer: Full answer text
            citations: List of citations used
        """
        from app.utils.cache import (
            get_conversation_session,
            save_conversation_session
        )

        import time

        session = await get_conversation_session(self.conversation_id)

        if not session:
            # Create new session
            session = {
                "session_id": self.conversation_id,
                "messages": [],
                "paper_ids": self.paper_ids,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        # Add user message
        session["messages"].append({
            "role": "user",
            "content": self.query,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

        # Add assistant message
        session["messages"].append({
            "role": "assistant",
            "content": answer,
            "citations": citations,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

        # Limit conversation history to last 20 messages
        if len(session["messages"]) > 20:
            session["messages"] = session["messages"][-20:]

        # Save session
        await save_conversation_session(self.conversation_id, session)


async def stream_rag_response(
    query: str,
    paper_ids: list[str],
    conversation_id: Optional[str] = None,
    query_type: str = "single",
    top_k: int = 5
) -> StreamingResponse:
    """
    High-level function to stream RAG response with real LLM generation.
    
    Retrieves relevant chunks from Milvus, then streams LLM answer.

    Args:
        query: User's question
        paper_ids: List of paper IDs to query
        conversation_id: Optional conversation session ID
        query_type: Type of query (single, cross_paper, evolution)
        top_k: Number of chunks to retrieve

    Returns:
        FastAPI StreamingResponse
    """
    from app.core.multimodal_search_service import get_multimodal_search_service
    from app.utils.zhipu_client import ZhipuLLMClient
    import asyncio
    
    # Retrieve relevant chunks
    service = get_multimodal_search_service()
    result = await service.search(
        query=query,
        paper_ids=paper_ids,
        user_id="stream",  # Placeholder for streaming
        top_k=top_k,
        use_reranker=True
    )
    
    # Build context from top chunks
    context_chunks = result.get("results", [])[:5]
    context_text = "\n\n---\n\n".join([
        f"[{i+1}] {chunk.get('content_data', '')}" 
        for i, chunk in enumerate(context_chunks)
    ])
    
    # Create LLM client
    llm_client = ZhipuLLMClient()
    
    # Generate streaming response
    async def generate_stream():
        try:
            system_prompt = """You are a helpful research assistant. Answer the user's question based on the provided context from academic papers.

Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite relevant parts using [1], [2], etc.
3. If the context doesn't contain enough information, say so
4. Keep the answer concise but comprehensive
5. Use markdown formatting for better readability"""

            user_message = f"""Context from papers:
{context_text}

Question: {query}

Please provide a comprehensive answer based on the context above."""

            # Stream from ZhipuAI
            stream_response = llm_client.client.chat.completions.create(
                model=llm_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1024,
                temperature=0.7,
                stream=True
            )
            
            # Yield tokens as they arrive
            for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    event = StreamToken(content=token)
                    yield format_sse_event(event.model_dump())
            
            # Send citations
            citations = []
            for i, chunk in enumerate(context_chunks[:5], 1):
                citations.append({
                    "citation_number": i,
                    "paper_id": chunk.get("paper_id"),
                    "content_preview": chunk.get("content_data", "")[:200],
                    "score": chunk.get("score", 0.0)
                })
            
            if citations:
                citation_event = StreamCitations(content=citations)
                yield format_sse_event(citation_event.model_dump())
            
            # Send done marker
            yield format_sse_done()
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_event = StreamError(content=str(e))
            yield format_sse_event(error_event.model_dump())
            yield format_sse_done()
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
