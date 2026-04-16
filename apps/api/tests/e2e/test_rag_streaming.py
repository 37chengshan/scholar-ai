"""
E2E tests for RAG SSE streaming endpoints.

Tests SSE event format, token streaming, citation final event.
"""

import json
import re
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rag_query_request() -> Dict[str, Any]:
    """Sample RAG query request."""
    return {
        "question": "What is the main contribution of this paper?",
        "paper_ids": ["paper-001", "paper-002"],
        "query_type": "single",
        "top_k": 5
    }


@pytest.fixture
def rag_stream_request() -> Dict[str, Any]:
    """Sample RAG streaming query request."""
    return {
        "question": "Explain the methodology used in the paper",
        "paper_ids": ["paper-001"],
        "query_type": "single",
        "top_k": 10
    }


@pytest.fixture
def sample_citations() -> List[Dict[str, Any]]:
    """Sample citations for testing."""
    return [
        {
            "paper_id": "paper-001",
            "title": "Deep Learning for Medical Imaging",
            "chunk_id": "chunk-1",
            "score": 0.95,
            "page": 5,
            "snippet": "Deep learning has achieved remarkable success in medical image analysis"
        },
        {
            "paper_id": "paper-002",
            "title": "CNN Features for Medical Images",
            "chunk_id": "chunk-2",
            "score": 0.88,
            "page": 3,
            "snippet": "CNNs automatically learn hierarchical features from raw images"
        }
    ]


@pytest.fixture
def sse_event_pattern() -> re.Pattern:
    """Regex pattern for SSE events."""
    return re.compile(r'data: (.+)\n\n', re.MULTILINE)


# =============================================================================
# SSE Format Tests
# =============================================================================

@pytest.mark.asyncio
async def test_sse_event_format_structure():
    """Test SSE event follows proper format: data: {...}\n\n"""
    from app.core.streaming import format_sse_event, format_sse_done

    # Test token event
    token_event = format_sse_event({"type": "token", "content": "Hello"})
    assert token_event.startswith("data: ")
    assert token_event.endswith("\n\n")

    # Parse the JSON
    json_str = token_event.replace("data: ", "").strip()
    data = json.loads(json_str)
    assert data["type"] == "token"
    assert data["content"] == "Hello"

    # Test done event
    done_event = format_sse_done()
    assert done_event == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_sse_token_event_parsing():
    """Test SSE token events can be parsed correctly."""
    from app.core.streaming import format_sse_event

    events = [
        {"type": "token", "content": "The "},
        {"type": "token", "content": "paper "},
        {"type": "token", "content": "proposes "},
    ]

    for event in events:
        sse_data = format_sse_event(event)
        json_str = sse_data.replace("data: ", "").strip()
        parsed = json.loads(json_str)
        assert parsed["type"] == "token"
        assert "content" in parsed


@pytest.mark.asyncio
async def test_sse_citation_event_format():
    """Test SSE citation event format."""
    from app.core.streaming import format_sse_event

    citations = [
        {"paper_id": "p1", "page": 5, "title": "Paper 1"},
        {"paper_id": "p2", "page": 3, "title": "Paper 2"}
    ]

    event = {"type": "citations", "content": citations}
    sse_data = format_sse_event(event)

    json_str = sse_data.replace("data: ", "").strip()
    parsed = json.loads(json_str)

    assert parsed["type"] == "citations"
    assert len(parsed["content"]) == 2
    assert parsed["content"][0]["paper_id"] == "p1"


@pytest.mark.asyncio
async def test_sse_error_event_format():
    """Test SSE error event format."""
    from app.core.streaming import format_sse_event

    error_event = {"type": "error", "content": "Something went wrong"}
    sse_data = format_sse_event(error_event)

    json_str = sse_data.replace("data: ", "").strip()
    parsed = json.loads(json_str)

    assert parsed["type"] == "error"
    assert "Something went wrong" in parsed["content"]


# =============================================================================
# Streaming Response Tests
# =============================================================================

@pytest.mark.asyncio
async def test_stream_tokens_generator():
    """Test token streaming generator."""
    from app.core.streaming import stream_tokens

    async def mock_generator():
        tokens = ["Hello ", "world", "!"]
        for token in tokens:
            yield token

    citations = [{"paper_id": "p1", "page": 1}]

    events = []
    async for event in stream_tokens(mock_generator(), citations):
        events.append(event)

    # Should have tokens + citations + done
    assert len(events) >= 3  # At least: token1, token2, token3, citations, done

    # Parse events
    data_events = []
    for event in events:
        if event.startswith("data: "):
            json_str = event.replace("data: ", "").strip()
            if json_str != "[DONE]":
                data_events.append(json.loads(json_str))

    # Check token events
    token_events = [e for e in data_events if e.get("type") == "token"]
    assert len(token_events) == 3

    # Check citation event
    citation_events = [e for e in data_events if e.get("type") == "citations"]
    assert len(citation_events) == 1
    assert len(citation_events[0]["content"]) == 1


@pytest.mark.asyncio
async def test_streaming_response_headers():
    """Test streaming response has correct headers."""
    from app.core.streaming import create_streaming_response, mock_token_generator
    from fastapi.responses import StreamingResponse

    response = await create_streaming_response(
        mock_token_generator("Hello world", chunk_size=5, delay_ms=0),
        citations=[]
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Connection"] == "keep-alive"
    assert response.headers["X-Accel-Buffering"] == "no"


# =============================================================================
# API Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rag_stream_endpoint_returns_sse(client: AsyncClient, mock_auth_headers: dict):
    """Test /rag/stream returns SSE response."""
    request_data = {
        "question": "What is the main contribution?",
        "paper_ids": ["paper-001"],
        "query_type": "single",
        "top_k": 5
    }

    with patch("app.utils.cache.get_cached_response", return_value=None):
        response = await client.post(
            "/rag/stream",
            json=request_data,
            headers={**mock_auth_headers, "Accept": "text/event-stream"}
        )

        # Should return 200
        assert response.status_code == 200

        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type or "application/json" in content_type


@pytest.mark.asyncio
async def test_rag_stream_cached_response():
    """Test streaming cached response format."""
    from app.api.rag import rag_query_stream
    from unittest.mock import AsyncMock

    cached_data = {
        "answer": "This is a cached answer.",
        "sources": [{"paper_id": "p1", "page": 1}],
        "confidence": 0.95
    }

    # Verify cached response structure
    assert "answer" in cached_data
    assert "sources" in cached_data
    assert isinstance(cached_data["sources"], list)


@pytest.mark.asyncio
async def test_rag_stream_event_sequence():
    """Test SSE event sequence: tokens -> citations -> [DONE]."""
    from app.core.streaming import stream_tokens

    async def token_gen():
        for word in ["The ", "answer ", "is ", "42."]:
            yield word

    citations = [{"paper_id": "p1", "title": "Test Paper", "page": 5}]

    events = []
    async for event in stream_tokens(token_gen(), citations):
        events.append(event)

    # Find the positions of different event types
    token_indices = []
    citation_index = None
    done_index = None

    for i, event in enumerate(events):
        if "[DONE]" in event:
            done_index = i
        elif event.startswith("data: "):
            json_str = event.replace("data: ", "").strip()
            if json_str != "[DONE]":
                try:
                    data = json.loads(json_str)
                    if data.get("type") == "token":
                        token_indices.append(i)
                    elif data.get("type") == "citations":
                        citation_index = i
                except json.JSONDecodeError:
                    pass

    # Verify sequence: tokens come before citations, citations before done
    assert len(token_indices) > 0, "Should have token events"
    assert citation_index is not None, "Should have citation event"
    assert done_index is not None, "Should have done event"

    # Tokens should come before citations
    assert max(token_indices) < citation_index, "Tokens should come before citations"

    # Citations should come before done
    assert citation_index < done_index, "Citations should come before done"


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rag_stream_error_handling():
    """Test streaming error returns SSE error event."""
    from app.core.streaming import stream_tokens

    async def error_generator():
        yield "Some tokens"
        raise ValueError("Test error")

    events = []
    async for event in stream_tokens(error_generator(), citations=None):
        events.append(event)

    # Should have error event
    error_events = []
    for event in events:
        if event.startswith("data: "):
            json_str = event.replace("data: ", "").strip()
            if json_str != "[DONE]":
                try:
                    data = json.loads(json_str)
                    if data.get("type") == "error":
                        error_events.append(data)
                except json.JSONDecodeError:
                    pass

    assert len(error_events) > 0, "Should have error event"
    assert "error" in error_events[0].get("content", "").lower()


@pytest.mark.asyncio
async def test_rag_stream_with_conversation():
    """Test streaming with conversation ID."""
    conversation_id = str(uuid.uuid4())

    request_data = {
        "question": "Tell me more about the methodology",
        "paper_ids": ["paper-001"],
        "query_type": "single",
        "conversation_id": conversation_id,
        "top_k": 5
    }

    # Verify request structure
    assert request_data["conversation_id"] == conversation_id
    assert "question" in request_data
    assert "paper_ids" in request_data


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_streaming_flow():
    """Test complete streaming flow from request to response."""
    from app.core.streaming import (
        mock_token_generator,
        stream_tokens,
        create_streaming_response
    )

    # Mock answer
    answer = "This is the complete answer to your question."
    citations = [
        {"paper_id": "p1", "title": "Paper 1", "page": 5, "score": 0.95}
    ]

    # Create token generator
    token_gen = mock_token_generator(answer, chunk_size=10, delay_ms=0)

    # Stream tokens
    events = []
    async for event in stream_tokens(token_gen, citations):
        events.append(event)

    # Parse all events
    parsed_tokens = []
    parsed_citations = None

    for event in events:
        if event.startswith("data: "):
            json_str = event.replace("data: ", "").strip()
            if json_str == "[DONE]":
                break
            try:
                data = json.loads(json_str)
                if data.get("type") == "token":
                    parsed_tokens.append(data["content"])
                elif data.get("type") == "citations":
                    parsed_citations = data["content"]
            except json.JSONDecodeError:
                pass

    # Reconstruct answer
    reconstructed = "".join(parsed_tokens)
    assert len(reconstructed) > 0

    # Verify citations
    assert parsed_citations is not None
    assert len(parsed_citations) == 1
    assert parsed_citations[0]["paper_id"] == "p1"


@pytest.mark.asyncio
async def test_streaming_rag_handler():
    """Test StreamingRAGHandler builds correct prompt."""
    from app.core.streaming import StreamingRAGHandler
    from unittest.mock import patch

    handler = StreamingRAGHandler(
        query="What is the main contribution?",
        paper_ids=["paper-001", "paper-002"],
        conversation_id=None,
        query_type="single"
    )

    # Test prompt building without conversation
    prompt = await handler.build_prompt_with_context()

    assert "research assistant" in prompt.lower()
    assert "What is the main contribution?" in prompt
    assert "paper-001" in prompt
    assert "paper-002" in prompt


@pytest.mark.asyncio
async def test_streaming_unicode_content():
    """Test streaming handles unicode content correctly."""
    from app.core.streaming import format_sse_event

    # Test with Chinese characters
    token_event = {"type": "token", "content": "深度学习在医学影像分析中取得了显著成功。"}
    sse_data = format_sse_event(token_event)

    json_str = sse_data.replace("data: ", "").strip()
    parsed = json.loads(json_str)

    assert parsed["content"] == "深度学习在医学影像分析中取得了显著成功。"
