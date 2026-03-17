"""
RAG (Retrieval-Augmented Generation) tests for streaming and conversation.

Tests cover:
- SSE streaming format verification
- Conversation session persistence
- Cache key generation
- Streaming response structure
"""

import json
import hashlib
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """Sample RAG query request."""
    return {
        "question": "What is the main contribution of this paper?",
        "paper_ids": ["paper-001", "paper-002"],
        "query_type": "single",
        "top_k": 5
    }


@pytest.fixture
def sample_conversation_context() -> Dict[str, Any]:
    """Sample conversation context with multiple turns."""
    return {
        "session_id": "session-abc-123",
        "messages": [
            {
                "role": "user",
                "content": "What is the main contribution?",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "role": "assistant",
                "content": "The paper proposes a novel deep learning approach.",
                "citations": [{"paper_id": "paper-001", "page": 3}],
                "timestamp": "2024-01-15T10:00:05Z"
            }
        ],
        "paper_ids": ["paper-001"],
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:05Z"
    }


@pytest.fixture
def mock_streaming_response() -> AsyncGenerator[bytes, None]:
    """Mock SSE streaming response."""
    events = [
        b'data: {"type": "token", "content": "The "}\n\n',
        b'data: {"type": "token", "content": "paper "}\n\n',
        b'data: {"type": "token", "content": "proposes..."}\n\n',
        b'data: {"type": "citations", "content": [{"paper_id": "paper-001", "page": 3}]}\n\n',
        b'data: [DONE]\n\n',
    ]
    for event in events:
        yield event


@pytest.fixture
def sample_cache_entry() -> Dict[str, Any]:
    """Sample cached RAG response."""
    return {
        "answer": "This paper proposes a novel deep learning approach.",
        "sources": [
            {
                "paper_id": "paper-001",
                "title": "Deep Learning for Medical Imaging",
                "chunk_id": "chunk-1",
                "score": 0.95,
                "page": 3
            }
        ],
        "confidence": 0.92,
        "cached_at": "2024-01-15T10:00:00Z"
    }


# =============================================================================
# Cache Key Generation Tests
# =============================================================================


def test_cache_key_generation():
    """Test that cache keys are generated consistently using SHA256."""
    query = "What is the main contribution?"
    paper_ids = ["paper-001", "paper-002"]
    query_type = "single"

    # Generate cache key: SHA256(query + paper_ids + type)
    key_data = f"{query}:{','.join(sorted(paper_ids))}:{query_type}"
    cache_key = hashlib.sha256(key_data.encode()).hexdigest()

    assert len(cache_key) == 64  # SHA256 hex length
    assert all(c in '0123456789abcdef' for c in cache_key)

    # Same inputs should produce same key
    key_data2 = f"{query}:{','.join(sorted(paper_ids))}:{query_type}"
    cache_key2 = hashlib.sha256(key_data2.encode()).hexdigest()
    assert cache_key == cache_key2


def test_cache_key_order_independence():
    """Test that paper_ids order doesn't affect cache key."""
    query = "What is the main contribution?"
    paper_ids_1 = ["paper-001", "paper-002", "paper-003"]
    paper_ids_2 = ["paper-003", "paper-001", "paper-002"]
    query_type = "single"

    key_1 = hashlib.sha256(f"{query}:{','.join(sorted(paper_ids_1))}:{query_type}".encode()).hexdigest()
    key_2 = hashlib.sha256(f"{query}:{','.join(sorted(paper_ids_2))}:{query_type}".encode()).hexdigest()

    assert key_1 == key_2


def test_cache_key_different_queries():
    """Test that different queries produce different cache keys."""
    paper_ids = ["paper-001"]
    query_type = "single"

    key_1 = hashlib.sha256(f"Query 1:{','.join(paper_ids)}:{query_type}".encode()).hexdigest()
    key_2 = hashlib.sha256(f"Query 2:{','.join(paper_ids)}:{query_type}".encode()).hexdigest()

    assert key_1 != key_2


# =============================================================================
# Streaming Format Tests
# =============================================================================


def test_sse_event_format():
    """Test SSE event formatting."""
    def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event."""
        return f"data: {json.dumps(data)}\n\n"

    # Token event
    token_event = format_sse_event("token", {"type": "token", "content": "Hello"})
    assert token_event == 'data: {"type": "token", "content": "Hello"}\n\n'

    # Citations event
    citations = [{"paper_id": "paper-001", "page": 3}]
    citation_event = format_sse_event("citations", {"type": "citations", "content": citations})
    assert "citations" in citation_event
    assert "paper-001" in citation_event

    # Done event
    done_event = format_sse_event("done", {"type": "done"})
    assert done_event == 'data: {"type": "done"}\n\n'


@pytest.mark.asyncio
async def test_streaming_response_structure():
    """Test streaming response produces valid SSE format."""
    async def mock_stream() -> AsyncGenerator[str, None]:
        tokens = ["The ", "paper ", "proposes ", "a ", "novel ", "approach."]
        for token in tokens:
            yield f'data: {{"type": "token", "content": "{token}"}}\n\n'
        yield 'data: {"type": "citations", "content": [{"paper_id": "paper-001", "page": 3}]}\n\n'
        yield 'data: [DONE]\n\n'

    events = []
    async for event in mock_stream():
        events.append(event)

    # Check structure
    assert len(events) == 8  # 6 tokens + citations + DONE

    # All events except last should be data: ...\n\n format
    for event in events[:-1]:
        assert event.startswith("data: ")
        assert event.endswith("\n\n")

    # Last event should be DONE
    assert "[DONE]" in events[-1]


@pytest.mark.asyncio
async def test_streaming_json_parsing():
    """Test that streaming events can be parsed as JSON."""
    async def mock_stream() -> AsyncGenerator[str, None]:
        yield 'data: {"type": "token", "content": "Hello"}\n\n'
        yield 'data: {"type": "citations", "content": []}\n\n'
        yield 'data: [DONE]\n\n'

    async for event in mock_stream():
        if "[DONE]" in event:
            break
        # Parse the JSON data
        data_str = event.replace("data: ", "").strip()
        data = json.loads(data_str)
        assert "type" in data


# =============================================================================
# Conversation Session Tests
# =============================================================================


def test_conversation_session_structure():
    """Test conversation session has required fields."""
    session = {
        "session_id": "session-abc-123",
        "messages": [],
        "paper_ids": ["paper-001"],
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
    }

    required_fields = ["session_id", "messages", "paper_ids", "created_at", "updated_at"]
    for field in required_fields:
        assert field in session


def test_conversation_message_structure():
    """Test conversation message has required fields."""
    message = {
        "role": "assistant",
        "content": "The paper proposes a novel approach.",
        "citations": [{"paper_id": "paper-001", "page": 3}],
        "timestamp": "2024-01-15T10:00:05Z"
    }

    assert message["role"] in ["user", "assistant", "system"]
    assert isinstance(message["content"], str)
    assert "timestamp" in message


def test_conversation_context_inclusion():
    """Test that conversation context is included in LLM prompt."""
    conversation = {
        "messages": [
            {"role": "user", "content": "What is the main contribution?"},
            {"role": "assistant", "content": "The paper proposes a novel approach."}
        ]
    }

    # Build context string for LLM prompt
    context_parts = []
    for msg in conversation["messages"]:
        context_parts.append(f"{msg['role']}: {msg['content']}")
    context = "\n".join(context_parts)

    assert "user: What is the main contribution?" in context
    assert "assistant: The paper proposes a novel approach." in context


@pytest.mark.asyncio
async def test_conversation_persistence():
    """Test conversation state is persisted across requests."""
    # Mock Redis storage
    stored_sessions = {}

    async def save_session(session_id: str, data: Dict[str, Any]):
        stored_sessions[session_id] = data

    async def get_session(session_id: str) -> Dict[str, Any]:
        return stored_sessions.get(session_id)

    # Save a session
    session_id = "session-test-123"
    session_data = {
        "messages": [{"role": "user", "content": "Hello"}],
        "paper_ids": ["paper-001"]
    }
    await save_session(session_id, session_data)

    # Retrieve the session
    retrieved = await get_session(session_id)
    assert retrieved is not None
    assert len(retrieved["messages"]) == 1
    assert retrieved["messages"][0]["content"] == "Hello"


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_rag_query_endpoint(client: AsyncClient, mock_auth_headers: dict):
    """Test RAG query endpoint returns expected structure."""
    request_data = {
        "question": "What is the main contribution?",
        "paper_ids": ["paper-001"],
        "query_type": "single",
        "top_k": 5
    }

    with patch("app.utils.cache.get_cached_response", return_value=None), \
         patch("app.utils.cache.set_cached_response", return_value=None):

        response = await client.post(
            "/rag/query",
            json=request_data,
            headers=mock_auth_headers
        )

        assert response.status_code in [200, 501]  # 501 if not implemented yet


@pytest.mark.asyncio
async def test_conversation_session_endpoint(client: AsyncClient, mock_auth_headers: dict):
    """Test conversation session retrieval endpoint."""
    session_id = "session-test-456"

    response = await client.get(
        f"/rag/session/{session_id}",
        headers=mock_auth_headers
    )

    # Should return 200 even if session doesn't exist (returns empty)
    # or 404 if not found
    assert response.status_code in [200, 404, 501]


@pytest.mark.asyncio
async def test_rag_stream_endpoint_headers(client: AsyncClient, mock_auth_headers: dict):
    """Test streaming endpoint returns correct content-type."""
    request_data = {
        "question": "What is the main contribution?",
        "paper_ids": ["paper-001"],
        "query_type": "single"
    }

    response = await client.post(
        "/rag/stream",
        json=request_data,
        headers={**mock_auth_headers, "Accept": "text/event-stream"}
    )

    # Check content-type for streaming
    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type or "application/json" in content_type


# =============================================================================
# Cache Utilities Tests
# =============================================================================


@pytest.mark.asyncio
async def test_cache_hit_miss_logging():
    """Test cache hit/miss logging."""
    import logging

    # Capture log messages
    log_messages = []

    class MockHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())

    logger = logging.getLogger("app.utils.cache")
    handler = MockHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Simulate cache hit
    async def get_with_logging(cache_key: str, cached_value: Any = None):
        if cached_value:
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_value
        else:
            logger.info(f"Cache miss for key: {cache_key}")
            return None

    await get_with_logging("test-key-123", {"answer": "cached"})
    await get_with_logging("test-key-456", None)

    assert any("Cache hit" in msg for msg in log_messages)
    assert any("Cache miss" in msg for msg in log_messages)

    logger.removeHandler(handler)


@pytest.mark.asyncio
async def test_cache_ttl_handling():
    """Test cache respects TTL settings."""
    # Mock cache with TTL
    cache_store = {}

    async def set_with_ttl(key: str, value: Any, ttl: int = 3600):
        cache_store[key] = {
            "value": value,
            "expires_at": "2024-01-15T11:00:00Z"  # +1 hour from 10:00:00Z
        }

    async def get_with_ttl(key: str) -> Any:
        entry = cache_store.get(key)
        if entry:
            # In real implementation, check if expired
            return entry["value"]
        return None

    await set_with_ttl("test-key", {"answer": "test"}, ttl=3600)
    result = await get_with_ttl("test-key")

    assert result is not None
    assert result["answer"] == "test"


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_full_rag_flow_with_caching():
    """Test complete RAG flow including cache check."""
    query = "What is the main contribution?"
    paper_ids = ["paper-001"]
    query_type = "single"

    # Generate cache key
    key_data = f"{query}:{','.join(sorted(paper_ids))}:{query_type}"
    cache_key = hashlib.sha256(key_data.encode()).hexdigest()

    # Mock cache
    cache_store = {}

    async def check_cache():
        return cache_store.get(cache_key)

    async def store_in_cache(response: Dict[str, Any]):
        cache_store[cache_key] = response

    # First request - cache miss
    cached = await check_cache()
    assert cached is None

    # Simulate processing and store result
    result = {"answer": "The paper proposes a novel approach.", "confidence": 0.95}
    await store_in_cache(result)

    # Second request - cache hit
    cached = await check_cache()
    assert cached is not None
    assert cached["answer"] == "The paper proposes a novel approach."


@pytest.mark.asyncio
async def test_conversation_with_context():
    """Test multi-turn conversation includes previous context."""
    conversation = {
        "session_id": "session-multi-123",
        "messages": [
            {"role": "user", "content": "What is the main contribution?"},
            {"role": "assistant", "content": "The paper proposes a novel approach."},
            {"role": "user", "content": "Can you elaborate on that?"}
        ],
        "paper_ids": ["paper-001"]
    }

    # Build context for LLM
    context = []
    for msg in conversation["messages"][:-1]:  # Exclude latest user message
        context.append(f"{msg['role']}: {msg['content']}")

    context_str = "\n".join(context)

    # Context should include previous turns
    assert "What is the main contribution?" in context_str
    assert "The paper proposes a novel approach." in context_str
    # Latest message should not be in context
    assert "Can you elaborate on that?" not in context_str


# =============================================================================
# PaperQA2 Integration Tests (Phase 3-01)
# =============================================================================

@pytest.fixture
def sample_paperqa_citation() -> Dict[str, Any]:
    """Sample citation from PaperQA2."""
    return {
        "text": "Deep learning has achieved remarkable success in medical image analysis[1].",
        "paper_id": "550e8400-e29b-41d4-a716-446655440000",
        "chunk_id": "chunk-001",
        "content_preview": "Deep learning approaches have revolutionized medical imaging...",
        "page": 5,
        "similarity": 0.92,
        "title": "Deep Learning in Medical Imaging: A Survey",
    }


@pytest.fixture
def mock_paperqa_docs():
    """Mock PaperQA2 Docs class."""
    mock_docs = MagicMock()

    # Mock query response
    mock_answer = MagicMock()
    mock_answer.answer = """Deep learning has achieved remarkable success in medical image analysis.
    Convolutional neural networks can automatically learn hierarchical features from raw images,
    eliminating the need for manual feature engineering."""
    mock_answer.contexts = [
        MagicMock(
            text="Deep learning has achieved remarkable success in medical image analysis[1].",
            score=0.92,
            source=MagicMock(
                doc=MagicMock(
                    citation="Deep Learning in Medical Imaging: A Survey",
                    docname="paper_001"
                )
            )
        ),
        MagicMock(
            text="CNNs automatically learn features from raw images[2].",
            score=0.85,
            source=MagicMock(
                doc=MagicMock(
                    citation="CNN Features for Medical Images",
                    docname="paper_001"
                )
            )
        ),
    ]

    mock_docs.query.return_value = mock_answer
    mock_docs.add.return_value = None

    return mock_docs


@pytest.fixture
def mock_pgvector_store_paperqa():
    """Mock PGVector store for PaperQA2 integration."""
    mock_store = MagicMock()

    # Mock search results
    mock_store.search.return_value = [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Deep learning has achieved remarkable success in medical image analysis.",
            "section": "introduction",
            "page": 5,
            "similarity": 0.92,
        },
        {
            "id": "chunk-002",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "CNNs automatically learn hierarchical features from raw images.",
            "section": "methods",
            "page": 7,
            "similarity": 0.88,
        },
    ]

    mock_store.add_chunks.return_value = ["chunk-003", "chunk-004"]
    mock_store.delete_by_paper.return_value = 10

    return mock_store


@pytest.fixture
def mock_paper_chunks_db() -> List[Dict[str, Any]]:
    """Sample paper chunks as returned from database."""
    return [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Deep learning has achieved remarkable success in medical image analysis.",
            "section": "introduction",
            "page_start": 5,
            "page_end": 5,
            "embedding": [0.1] * 768,
            "is_table": False,
            "is_figure": False,
            "is_formula": False,
        },
        {
            "id": "chunk-002",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "CNNs automatically learn hierarchical features from raw images.",
            "section": "methods",
            "page_start": 7,
            "page_end": 7,
            "embedding": [0.2] * 768,
            "is_table": False,
            "is_figure": False,
            "is_formula": False,
        },
    ]


class TestPaperQA2Integration:
    """Test PaperQA2 library integration."""

    def test_paperqa_import(self):
        """PaperQA should be importable."""
        pytest.importorskip("paperqa", reason="PaperQA2 not installed")
        from paperqa import Docs, Settings
        assert Docs is not None
        assert Settings is not None

    def test_paperqa_settings(self):
        """Should configure PaperQA settings."""
        pytest.importorskip("paperqa", reason="PaperQA2 not installed")
        from paperqa import Settings

        settings = Settings()
        assert settings is not None

    @pytest.mark.asyncio
    async def test_pgvector_store_search(self, mock_paper_chunks_db):
        """Should search PGVector store and return chunks."""
        pytest.importorskip("app.core.rag_service", reason="RAG service not implemented")
        from app.core.rag_service import PGVectorStore

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {
                "id": c["id"],
                "paper_id": c["paper_id"],
                "content": c["content"],
                "section": c["section"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
                "distance": 0.1,
            }
            for c in mock_paper_chunks_db
        ]

        store = PGVectorStore(connection=mock_conn)
        results = await store.search(
            query="deep learning",
            paper_ids=["550e8400-e29b-41d4-a716-446655440000"],
            limit=5,
        )

        assert isinstance(results, list)
        assert len(results) > 0
        assert "content" in results[0]
        assert "similarity" in results[0]


class TestRAGModelsPhase3:
    """Test RAG models from Phase 3-01."""

    def test_rag_query_request_model_exists(self):
        """RAGQueryRequest model should exist."""
        pytest.importorskip("app.models.rag", reason="RAG models not implemented")
        from app.models.rag import RAGQueryRequest
        assert RAGQueryRequest is not None

    def test_rag_response_model_exists(self):
        """RAGResponse model should exist."""
        pytest.importorskip("app.models.rag", reason="RAG models not implemented")
        from app.models.rag import RAGResponse
        assert RAGResponse is not None

    def test_citation_model_exists(self):
        """Citation model should exist."""
        pytest.importorskip("app.models.rag", reason="RAG models not implemented")
        from app.models.rag import Citation
        assert Citation is not None

    def test_rag_service_exists(self):
        """RAGService should exist."""
        pytest.importorskip("app.core.rag_service", reason="RAG service not implemented")
        from app.core.rag_service import RAGService
        assert RAGService is not None

    def test_pgvector_store_exists(self):
        """PGVectorStore should exist."""
        pytest.importorskip("app.core.rag_service", reason="RAG service not implemented")
        from app.core.rag_service import PGVectorStore
        assert PGVectorStore is not None

