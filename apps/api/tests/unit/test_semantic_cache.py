"""Unit tests for SemanticCache class.

Tests the semantic similarity-based caching system for RAG queries.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.core.semantic_cache import SemanticCache


class AsyncIteratorMock:
    """Helper class to mock async iterators."""
    
    def __init__(self, items):
        self.items = items
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


@pytest.fixture
def semantic_cache():
    """Create SemanticCache instance with default settings and mocked embedding service."""
    with patch('app.core.semantic_cache.EmbeddingService') as mock_embedding_class:
        mock_instance = MagicMock()
        mock_instance.generate_embedding = MagicMock(return_value=[0.1] * 768)
        mock_embedding_class.return_value = mock_instance
        cache = SemanticCache(threshold=0.95, ttl=86400)
        # Store the mock for later use in tests
        cache._mock_embedding = mock_instance
        yield cache


@pytest.fixture
def mock_redis():
    """Mock Redis database for testing."""
    with patch('app.core.semantic_cache.redis_db') as mock:
        mock.client = MagicMock()
        # Use a callable that returns an async iterator
        mock.client.scan_iter = MagicMock()
        mock.get = AsyncMock()
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        yield mock


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for testing."""
    with patch('app.core.semantic_cache.EmbeddingService') as mock:
        mock_instance = MagicMock()
        mock_instance.generate_embedding = MagicMock(return_value=[0.1] * 768)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_cache_miss_no_keys(semantic_cache, mock_redis):
    """Test 1: get() returns None for cache miss (no similar queries cached)."""
    # No keys in Redis
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock([])

    result = await semantic_cache.get("What is machine learning?", ["paper-1"])

    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_exact_match(semantic_cache, mock_redis):
    """Test 2: get() returns cached response for exact query match."""
    # Mock cached data with embedding that will match exactly
    cached_response = {"answer": "ML is...", "sources": []}
    cached_embedding = [0.5] * 768  # Same as query embedding

    mock_redis.client.scan_iter.return_value = AsyncIteratorMock(["rag:semantic_cache:abc123:paper-1"])
    mock_redis.get.return_value = json.dumps({
        "query": "What is machine learning?",
        "embedding": cached_embedding,
        "response": cached_response,
        "paper_ids": ["paper-1"],
        "timestamp": 1234567890.0
    })

    # Mock embedding service to return same embedding (exact match)
    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=cached_embedding):
        result = await semantic_cache.get("What is machine learning?", ["paper-1"])

    assert result == cached_response


@pytest.mark.asyncio
async def test_cache_hit_similar_query(semantic_cache, mock_redis):
    """Test 3: get() returns cached response for semantically similar query (similarity >= 0.95)."""
    # Create two similar embeddings (cosine similarity >= 0.95)
    base_embedding = [0.5] * 768
    # Slightly modify to create a similar but not identical embedding
    similar_embedding = base_embedding.copy()
    for i in range(0, 768, 100):
        similar_embedding[i] += 0.01  # Small perturbation

    cached_response = {"answer": "Deep learning is...", "sources": []}
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock(["rag:semantic_cache:xyz:paper-1"])
    mock_redis.get.return_value = json.dumps({
        "query": "What is deep learning?",
        "embedding": base_embedding,
        "response": cached_response,
        "paper_ids": ["paper-1"],
        "timestamp": 1234567890.0
    })

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=similar_embedding):
        result = await semantic_cache.get("Explain deep learning", ["paper-1"])

    # Should hit because similarity >= 0.95 (base_embedding and similar_embedding are very close)
    assert result == cached_response


@pytest.mark.asyncio
async def test_cache_miss_dissimilar_query(semantic_cache, mock_redis):
    """Test 4: get() returns None for dissimilar query (similarity < 0.95)."""
    # Create very different embeddings (orthogonal = similarity near 0)
    cached_embedding = [1.0] * 384 + [-1.0] * 384  # 768 dims, half positive half negative
    query_embedding = [-1.0] * 384 + [1.0] * 384  # Opposite signs

    cached_response = {"answer": "Answer", "sources": []}
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock(["rag:semantic_cache:abc:paper-1"])
    mock_redis.get.return_value = json.dumps({
        "query": "What is AI?",
        "embedding": cached_embedding,
        "response": cached_response,
        "paper_ids": ["paper-1"],
        "timestamp": 1234567890.0
    })

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=query_embedding):
        result = await semantic_cache.get("How to cook pasta?", ["paper-1"])

    # Should miss because similarity < 0.95 (orthogonal vectors)
    assert result is None


@pytest.mark.asyncio
async def test_set_stores_embedding(semantic_cache, mock_redis):
    """Test 5: set() stores query embedding with response in Redis."""
    mock_redis.set.return_value = True

    response = {"answer": "Test answer", "sources": [], "confidence": 0.8}
    embedding = [0.1] * 768

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=embedding):
        result = await semantic_cache.set("Test query", ["paper-1"], response)

    assert result is True
    mock_redis.set.assert_called_once()

    # Verify TTL is 86400 (24 hours) - passed as keyword argument 'expire'
    call_args = mock_redis.set.call_args
    assert call_args.kwargs.get('expire') == 86400

    # Verify stored data contains embedding
    stored_data = json.loads(call_args.args[1])
    assert stored_data["embedding"] == embedding
    assert stored_data["response"] == response


@pytest.mark.asyncio
async def test_cache_entry_expiry(semantic_cache, mock_redis):
    """Test 6: Cache entries expire after TTL (24 hours)."""
    # This test verifies TTL is set correctly
    # Actual expiry is handled by Redis automatically
    mock_redis.set.return_value = True

    response = {"answer": "Test", "sources": []}

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=[0.1] * 768):
        await semantic_cache.set("Query", ["paper-1"], response)

    # Verify TTL was set to 86400 seconds (passed as keyword argument)
    call_args = mock_redis.set.call_args
    ttl = call_args.kwargs.get('expire', 0)

    assert ttl == 86400, f"TTL should be 86400 (24 hours), got {ttl}"


@pytest.mark.asyncio
async def test_clear_removes_entries(semantic_cache, mock_redis):
    """Test 7: clear() removes all cache entries."""
    # Mock Redis returning keys to delete
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock([
        "rag:semantic_cache:key1:paper-1",
        "rag:semantic_cache:key2:paper-1"
    ])
    mock_redis.delete.return_value = 1

    count = await semantic_cache.clear(["paper-1"])

    assert count == 2
    assert mock_redis.delete.call_count == 2


@pytest.mark.asyncio
async def test_clear_all_entries(semantic_cache, mock_redis):
    """Test clear() without paper_ids removes all semantic cache entries."""
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock([
        "rag:semantic_cache:key1:paper-1",
        "rag:semantic_cache:key2:paper-2"
    ])
    mock_redis.delete.return_value = 1

    count = await semantic_cache.clear()

    assert count == 2


@pytest.mark.asyncio
async def test_get_with_empty_paper_ids(semantic_cache, mock_redis):
    """Test get() handles empty paper_ids list."""
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock([])

    result = await semantic_cache.get("Query", [])

    assert result is None


@pytest.mark.asyncio
async def test_set_with_query_type(semantic_cache, mock_redis):
    """Test set() stores query_type in cache data."""
    mock_redis.set.return_value = True

    response = {"answer": "Test", "sources": []}

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=[0.1] * 768):
        await semantic_cache.set("Query", ["paper-1"], response, query_type="cross_paper")

    call_args = mock_redis.set.call_args
    stored_data = json.loads(call_args.args[1])
    assert stored_data["query_type"] == "cross_paper"


def test_cosine_similarity_calculation(semantic_cache):
    """Test cosine similarity calculation is correct."""
    # Test with known vectors
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]  # Same vector, similarity should be 1.0

    similarity = semantic_cache._cosine_similarity(a, b)
    assert similarity == 1.0

    # Orthogonal vectors
    c = [0.0, 1.0, 0.0]
    similarity = semantic_cache._cosine_similarity(a, c)
    assert similarity == 0.0

    # Opposite vectors
    d = [-1.0, 0.0, 0.0]
    similarity = semantic_cache._cosine_similarity(a, d)
    assert similarity == -1.0


@pytest.mark.asyncio
async def test_get_handles_invalid_cached_data(semantic_cache, mock_redis):
    """Test get() handles invalid/malformed cached data gracefully."""
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock(["rag:semantic_cache:key:paper-1"])
    # Return invalid JSON
    mock_redis.get.return_value = "invalid json data"

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=[0.1] * 768):
        result = await semantic_cache.get("Query", ["paper-1"])

    # Should return None for invalid data
    assert result is None


@pytest.mark.asyncio
async def test_get_handles_missing_embedding(semantic_cache, mock_redis):
    """Test get() handles cached data without embedding field."""
    mock_redis.client.scan_iter.return_value = AsyncIteratorMock(["rag:semantic_cache:key:paper-1"])
    # Return data without embedding
    mock_redis.get.return_value = json.dumps({
        "query": "Test",
        "response": {"answer": "test"}
    })

    with patch.object(semantic_cache.embedding_service, 'generate_embedding', return_value=[0.1] * 768):
        result = await semantic_cache.get("Query", ["paper-1"])

    # Should return None when embedding is missing
    assert result is None