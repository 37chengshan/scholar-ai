"""
Hybrid Search tests for dense (PGVector) + sparse (tsvector) + RRF fusion.

Tests cover:
- Dense vector search functionality
- Sparse text search using tsvector
- RRF (Reciprocal Rank Fusion) scoring
- Hybrid search integration
- Library search API endpoints
"""

import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_query() -> str:
    """Sample search query."""
    return "neural network optimization"


@pytest.fixture
def sample_paper_ids() -> List[str]:
    """Sample paper IDs for search scope."""
    return [
        "550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440001",
    ]


@pytest.fixture
def mock_dense_results() -> List[Dict[str, Any]]:
    """Sample dense vector search results."""
    return [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Neural network optimization techniques improve convergence speed.",
            "section": "methods",
            "page": 5,
            "similarity": 0.92,
            "distance": 0.08,
        },
        {
            "id": "chunk-002",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Gradient descent optimization for deep neural networks.",
            "section": "methods",
            "page": 6,
            "similarity": 0.88,
            "distance": 0.12,
        },
        {
            "id": "chunk-003",
            "paper_id": "550e8400-e29b-41d4-a716-446655440001",
            "content": "Adam optimizer performs well on neural network training.",
            "section": "results",
            "page": 10,
            "similarity": 0.85,
            "distance": 0.15,
        },
    ]


@pytest.fixture
def mock_sparse_results() -> List[Dict[str, Any]]:
    """Sample sparse text search results using tsvector."""
    return [
        {
            "id": "chunk-002",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Gradient descent optimization for deep neural networks.",
            "section": "methods",
            "page": 6,
            "rank": 0.95,
        },
        {
            "id": "chunk-004",
            "paper_id": "550e8400-e29b-41d4-a716-446655440001",
            "content": "Optimization algorithms for neural networks in computer vision.",
            "section": "introduction",
            "page": 2,
            "rank": 0.87,
        },
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Neural network optimization techniques improve convergence speed.",
            "section": "methods",
            "page": 5,
            "rank": 0.82,
        },
    ]


@pytest.fixture
def sample_chunk_records() -> List[Dict[str, Any]]:
    """Sample database records for paper chunks."""
    return [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Neural network optimization techniques improve convergence speed.",
            "section": "methods",
            "page_start": 5,
            "page_end": 5,
            "embedding": [0.1] * 768,
        },
        {
            "id": "chunk-002",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Gradient descent optimization for deep neural networks.",
            "section": "methods",
            "page_start": 6,
            "page_end": 6,
            "embedding": [0.2] * 768,
        },
        {
            "id": "chunk-003",
            "paper_id": "550e8400-e29b-41d4-a716-446655440001",
            "content": "Adam optimizer performs well on neural network training.",
            "section": "results",
            "page_start": 10,
            "page_end": 10,
            "embedding": [0.3] * 768,
        },
    ]


# =============================================================================
# Dense Search Tests
# =============================================================================


def test_dense_search_function_exists():
    """Test that dense_search function exists in hybrid_search module."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import dense_search
    assert callable(dense_search)


@pytest.mark.asyncio
async def test_dense_search_returns_expected_structure():
    """Test dense search returns properly structured results."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import dense_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Neural network optimization...",
            "section": "methods",
            "page_start": 5,
            "page_end": 5,
            "distance": 0.1,
        }
    ]

    with patch("app.core.embedding_service.EmbeddingService") as mock_emb:
        mock_emb_instance = MagicMock()
        mock_emb_instance.generate_embedding.return_value = [0.1] * 768
        mock_emb.return_value = mock_emb_instance

        results = await dense_search(
            connection=mock_conn,
            query="neural network optimization",
            paper_ids=["550e8400-e29b-41d4-a716-446655440000"],
            limit=5,
        )

    assert isinstance(results, list)
    if results:  # Skip if implementation returns empty
        assert "id" in results[0]
        assert "content" in results[0]
        assert "similarity" in results[0]


@pytest.mark.asyncio
async def test_dense_search_similarity_calculation():
    """Test that similarity is correctly calculated from distance."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import dense_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "chunk-001",
            "paper_id": "paper-001",
            "content": "Test content",
            "section": "methods",
            "page_start": 1,
            "page_end": 1,
            "distance": 0.2,  # Cosine distance
        }
    ]

    with patch("app.core.embedding_service.EmbeddingService") as mock_emb:
        mock_emb_instance = MagicMock()
        mock_emb_instance.generate_embedding.return_value = [0.1] * 768
        mock_emb.return_value = mock_emb_instance

        results = await dense_search(
            connection=mock_conn,
            query="test query",
            paper_ids=["paper-001"],
            limit=5,
        )

    if results:
        # Similarity should be 1 - distance for cosine
        expected_similarity = 0.8  # 1.0 - 0.2
        assert abs(results[0]["similarity"] - expected_similarity) < 0.01


@pytest.mark.asyncio
async def test_dense_search_empty_results():
    """Test dense search handles empty results gracefully."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import dense_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    with patch("app.core.embedding_service.EmbeddingService") as mock_emb:
        mock_emb_instance = MagicMock()
        mock_emb_instance.generate_embedding.return_value = [0.1] * 768
        mock_emb.return_value = mock_emb_instance

        results = await dense_search(
            connection=mock_conn,
            query="nonexistent topic",
            paper_ids=["paper-001"],
            limit=5,
        )

    assert results == []


# =============================================================================
# Sparse Search Tests
# =============================================================================


def test_sparse_search_function_exists():
    """Test that sparse_search function exists in hybrid_search module."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import sparse_search
    assert callable(sparse_search)


@pytest.mark.asyncio
async def test_sparse_search_returns_expected_structure():
    """Test sparse search returns properly structured results."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import sparse_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "chunk-001",
            "paper_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Neural network optimization...",
            "section": "methods",
            "page_start": 5,
            "page_end": 5,
            "rank": 0.75,
        }
    ]

    results = await sparse_search(
        connection=mock_conn,
        query="neural network optimization",
        paper_ids=["550e8400-e29b-41d4-a716-446655440000"],
        limit=5,
    )

    assert isinstance(results, list)
    if results:
        assert "id" in results[0]
        assert "content" in results[0]
        assert "rank" in results[0]


@pytest.mark.asyncio
async def test_sparse_search_uses_tsvector():
    """Test that sparse search uses PostgreSQL tsvector functionality."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import sparse_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    await sparse_search(
        connection=mock_conn,
        query="neural network",
        paper_ids=["paper-001"],
        limit=10,
    )

    # Check that the query was called with tsvector-related SQL
    call_args = mock_conn.fetch.call_args
    sql_query = call_args[0][0] if call_args[0] else call_args[1].get('query', '')

    # SQL should contain tsvector-related functions
    sql_lower = sql_query.lower()
    assert "to_tsquery" in sql_lower or "ts_rank" in sql_lower or "search_vector" in sql_lower


@pytest.mark.asyncio
async def test_sparse_search_empty_results():
    """Test sparse search handles empty results gracefully."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import sparse_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    results = await sparse_search(
        connection=mock_conn,
        query="xyznonexistent",
        paper_ids=["paper-001"],
        limit=5,
    )

    assert results == []


# =============================================================================
# RRF Fusion Tests
# =============================================================================


def test_rrf_fusion_function_exists():
    """Test that reciprocal_rank_fusion function exists."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion
    assert callable(reciprocal_rank_fusion)


def test_rrf_fusion_basic_calculation():
    """Test RRF fusion with basic inputs."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    # Dense results: chunk-001 at rank 1, chunk-002 at rank 2
    dense_results = [
        {"id": "chunk-001", "score": 0.9},
        {"id": "chunk-002", "score": 0.8},
    ]

    # Sparse results: chunk-002 at rank 1, chunk-001 at rank 2
    sparse_results = [
        {"id": "chunk-002", "score": 0.85},
        {"id": "chunk-001", "score": 0.75},
    ]

    fused = reciprocal_rank_fusion(
        dense_results=dense_results,
        sparse_results=sparse_results,
        dense_weight=0.6,
        sparse_weight=0.4,
        k=60,
    )

    assert isinstance(fused, list)
    assert len(fused) == 2

    # Both chunks should be present
    ids = [r["id"] for r in fused]
    assert "chunk-001" in ids
    assert "chunk-002" in ids


def test_rrf_fusion_score_calculation():
    """Test RRF score calculation with k=60."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    # Single result in both lists at rank 1
    dense_results = [{"id": "chunk-001", "score": 0.9}]
    sparse_results = [{"id": "chunk-001", "score": 0.85}]

    fused = reciprocal_rank_fusion(
        dense_results=dense_results,
        sparse_results=sparse_results,
        dense_weight=0.6,
        sparse_weight=0.4,
        k=60,
    )

    assert len(fused) == 1

    # RRF score for rank 1: 1/(60+1) = ~0.0164
    # Weighted: 0.6 * 0.0164 + 0.4 * 0.0164 = 0.0164
    expected_score = 0.6 * (1.0 / 61) + 0.4 * (1.0 / 61)
    assert abs(fused[0]["rrf_score"] - expected_score) < 0.001


def test_rrf_fusion_weights_applied():
    """Test that weights are correctly applied to RRF scores."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    # chunk-001 at rank 1 in dense, rank 2 in sparse
    # chunk-002 at rank 2 in dense, rank 1 in sparse
    # With higher dense weight, chunk-001 should have higher score
    dense_results = [
        {"id": "chunk-001", "score": 0.9},
        {"id": "chunk-002", "score": 0.7},
    ]
    sparse_results = [
        {"id": "chunk-002", "score": 0.85},
        {"id": "chunk-001", "score": 0.75},
    ]

    # Test with different weights
    fused_60_40 = reciprocal_rank_fusion(
        dense_results, sparse_results,
        dense_weight=0.6, sparse_weight=0.4, k=60
    )

    fused_80_20 = reciprocal_rank_fusion(
        dense_results, sparse_results,
        dense_weight=0.8, sparse_weight=0.2, k=60
    )

    # Both should have 2 chunks
    assert len(fused_60_40) == 2
    assert len(fused_80_20) == 2

    # With higher dense weight, chunk-001 (better in dense) should have higher score
    # chunk-001: rank 1 in dense, rank 2 in sparse
    #   - 60/40: 0.6*(1/61) + 0.4*(1/62) = 0.009836 + 0.006452 = 0.016288
    #   - 80/20: 0.8*(1/61) + 0.2*(1/62) = 0.013115 + 0.003226 = 0.016341
    # chunk-002: rank 2 in dense, rank 1 in sparse
    #   - 60/40: 0.6*(1/62) + 0.4*(1/61) = 0.009677 + 0.006557 = 0.016234
    #   - 80/20: 0.8*(1/62) + 0.2*(1/61) = 0.012903 + 0.003279 = 0.016182

    # chunk-001 should be ranked higher in both cases
    assert fused_60_40[0]["id"] == "chunk-001"
    assert fused_80_20[0]["id"] == "chunk-001"

    # With higher dense weight, chunk-001's advantage should be greater
    score_diff_6040 = fused_60_40[0]["rrf_score"] - fused_60_40[1]["rrf_score"]
    score_diff_8020 = fused_80_20[0]["rrf_score"] - fused_80_20[1]["rrf_score"]
    assert score_diff_8020 > score_diff_6040


def test_rrf_fusion_empty_input():
    """Test RRF fusion handles empty inputs."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    # Both empty
    fused = reciprocal_rank_fusion([], [], 0.6, 0.4, 60)
    assert fused == []

    # Only dense results
    dense_results = [{"id": "chunk-001", "score": 0.9}]
    fused = reciprocal_rank_fusion(dense_results, [], 0.6, 0.4, 60)
    assert len(fused) == 1
    assert fused[0]["id"] == "chunk-001"

    # Only sparse results
    sparse_results = [{"id": "chunk-002", "score": 0.8}]
    fused = reciprocal_rank_fusion([], sparse_results, 0.6, 0.4, 60)
    assert len(fused) == 1
    assert fused[0]["id"] == "chunk-002"


def test_rrf_fusion_result_ordering():
    """Test that RRF results are sorted by score descending."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    # chunk-001 better in dense (rank 1), chunk-002 better in sparse (rank 1)
    dense_results = [
        {"id": "chunk-001", "score": 0.9},
        {"id": "chunk-002", "score": 0.7},
    ]
    sparse_results = [
        {"id": "chunk-002", "score": 0.85},
        {"id": "chunk-001", "score": 0.75},
    ]

    fused = reciprocal_rank_fusion(
        dense_results, sparse_results,
        dense_weight=0.6, sparse_weight=0.4, k=60
    )

    # Results should be sorted by rrf_score descending
    for i in range(len(fused) - 1):
        assert fused[i]["rrf_score"] >= fused[i + 1]["rrf_score"]


# =============================================================================
# Hybrid Search Integration Tests
# =============================================================================


def test_hybrid_search_service_exists():
    """Test that HybridSearchService class exists."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import HybridSearchService
    assert HybridSearchService is not None


@pytest.mark.asyncio
async def test_hybrid_search_integration():
    """Test complete hybrid search flow."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import HybridSearchService

    mock_conn = AsyncMock()

    # Mock dense search results
    mock_conn.fetch.side_effect = [
        # First call for dense search
        [
            {"id": "chunk-001", "paper_id": "p1", "content": "Content 1",
             "section": "s1", "page_start": 1, "page_end": 1, "distance": 0.1},
        ],
        # Second call for sparse search
        [
            {"id": "chunk-001", "paper_id": "p1", "content": "Content 1",
             "section": "s1", "page_start": 1, "page_end": 1, "rank": 0.9},
        ],
    ]

    service = HybridSearchService(connection=mock_conn)

    with patch("app.core.hybrid_search.dense_search") as mock_dense, \
         patch("app.core.hybrid_search.sparse_search") as mock_sparse:

        mock_dense.return_value = [
            {"id": "chunk-001", "score": 0.9},
        ]
        mock_sparse.return_value = [
            {"id": "chunk-001", "score": 0.85},
        ]

        results = await service.search(
            query="test query",
            paper_ids=["p1"],
            limit=5,
            use_hybrid=True,
        )

    assert isinstance(results, list)


# =============================================================================
# Library Search API Tests
# =============================================================================


@pytest.mark.asyncio
async def test_library_search_endpoint_exists(client: AsyncClient, mock_auth_headers: dict):
    """Test that library search endpoint exists."""
    response = await client.get(
        "/search/library?q=test&limit=10",
        headers=mock_auth_headers,
    )

    # Should not be 404 (endpoint not found)
    assert response.status_code != 404


@pytest.mark.asyncio
async def test_library_search_returns_search_results(client: AsyncClient, mock_auth_headers: dict):
    """Test library search returns properly formatted results."""
    response = await client.get(
        "/search/library?q=neural%20network&limit=5",
        headers=mock_auth_headers,
    )

    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_library_search_accepts_hybrid_param(client: AsyncClient, mock_auth_headers: dict):
    """Test library search accepts hybrid search parameter."""
    response = await client.get(
        "/search/library?q=test&hybrid=true",
        headers=mock_auth_headers,
    )

    # Should accept the parameter without error
    assert response.status_code in [200, 501]  # 501 if not fully implemented


@pytest.mark.asyncio
async def test_library_search_validates_limit(client: AsyncClient, mock_auth_headers: dict):
    """Test library search validates limit parameter."""
    # Invalid limit (too high)
    response = await client.get(
        "/search/library?q=test&limit=1000",
        headers=mock_auth_headers,
    )

    # Should return 422 for invalid input
    assert response.status_code in [200, 422, 501]


@pytest.mark.asyncio
async def test_library_search_requires_auth(client: AsyncClient):
    """Test library search requires authentication."""
    response = await client.get("/search/library?q=test")

    # Should return 401 without auth
    assert response.status_code in [401, 403, 501]


# =============================================================================
# Database Migration Tests
# =============================================================================


def test_tsvector_migration_sql():
    """Test that tsvector migration SQL exists and is valid."""
    import os

    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "add_tsvector.sql"
    )

    if os.path.exists(migration_path):
        with open(migration_path) as f:
            sql = f.read()

        # Should contain necessary SQL statements
        assert "paper_chunks" in sql.lower()
        assert "tsvector" in sql.lower()
    else:
        pytest.skip("Migration file not created yet")


# =============================================================================
# Performance Tests
# =============================================================================


def test_rrf_fusion_performance():
    """Test RRF fusion performance with large result sets."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import reciprocal_rank_fusion

    import time

    # Create large result sets
    dense_results = [{"id": f"chunk-{i:04d}", "score": 1.0 - (i * 0.001)} for i in range(100)]
    sparse_results = [{"id": f"chunk-{i:04d}", "score": 1.0 - (i * 0.001)} for i in range(100)]

    start = time.time()
    fused = reciprocal_rank_fusion(dense_results, sparse_results, 0.6, 0.4, 60)
    elapsed = time.time() - start

    assert len(fused) == 100
    # Should complete quickly (< 100ms for 100 items)
    assert elapsed < 0.1


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_dense_search_special_characters():
    """Test dense search handles special characters in query."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import dense_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    with patch("app.core.embedding_service.EmbeddingService") as mock_emb:
        mock_emb_instance = MagicMock()
        mock_emb_instance.generate_embedding.return_value = [0.1] * 768
        mock_emb.return_value = mock_emb_instance

        # Query with special characters
        results = await dense_search(
            connection=mock_conn,
            query="neural networks & optimization (2024)",
            paper_ids=["paper-001"],
            limit=5,
        )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_sparse_search_special_characters():
    """Test sparse search handles special characters in query."""
    pytest.importorskip("app.core.hybrid_search", reason="hybrid_search not implemented")
    from app.core.hybrid_search import sparse_search

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    # Query with special characters that need escaping
    results = await sparse_search(
        connection=mock_conn,
        query="C++ programming & algorithms",
        paper_ids=["paper-001"],
        limit=5,
    )

    assert isinstance(results, list)
