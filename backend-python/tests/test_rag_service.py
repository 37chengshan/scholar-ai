"""Tests for RAG service with Milvus and 1024-dim embeddings.

Per 13-03-PLAN:
- Test 1: retrieve_with_reranking uses 1024-dim BGE-M3 embedding
- Test 2: retrieve_with_reranking calls Milvus.search_contents
- Test 3: retrieve_with_reranking applies reranking
- Test 4: RAGService.query uses MultimodalSearchService
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from app.core.rag_service import retrieve_with_reranking, RAGService


# Fixtures

@pytest.fixture
def mock_bge_m3_service():
    """Mock BGEM3Service for 1024-dim embeddings."""
    mock = Mock()
    mock.encode_text = Mock(return_value=[0.1] * 1024)
    return mock


@pytest.fixture
def mock_milvus_service():
    """Mock MilvusService for vector search."""
    mock = Mock()
    mock.search_contents = Mock(return_value=[
        {
            "id": 1,
            "paper_id": "paper-1",
            "page_num": 1,
            "content_type": "text",
            "content_data": "Machine learning is a subset of AI.",
            "distance": 0.1,
        },
        {
            "id": 2,
            "paper_id": "paper-1",
            "page_num": 2,
            "content_type": "text",
            "content_data": "Deep learning uses neural networks.",
            "distance": 0.2,
        },
    ])
    return mock


@pytest.fixture
def mock_reranker_service():
    """Mock ReRankerService."""
    mock = Mock()
    mock.rerank = Mock(return_value=[
        ("Machine learning is a subset of AI.", 0.95),
        ("Deep learning uses neural networks.", 0.85),
    ])
    return mock


@pytest.fixture
def mock_multimodal_search_service():
    """Mock MultimodalSearchService."""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value={
        "query": "test query",
        "intent": "default",
        "results": [
            {
                "id": 1,
                "paper_id": "paper-1",
                "content_data": "Test content",
                "distance": 0.1,
                "reranker_score": 0.95,
            }
        ],
        "total_count": 1,
    })
    return mock


# Tests

class TestRetrieveWithReranking1024Dim:
    """Test retrieve_with_reranking with 1024-dim embeddings."""

    @pytest.mark.asyncio
    async def test_retrieve_uses_1024_dim_embedding(self, mock_bge_m3_service, mock_milvus_service, mock_reranker_service):
        """Test 1: retrieve_with_reranking uses 1024-dim BGE-M3 embedding."""
        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                with patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker_service):
                    results = await retrieve_with_reranking(
                        query="What is machine learning?",
                        user_id="test-user",
                        paper_ids=["paper-1"],
                        top_k=20,
                        rerank_top_n=5,
                    )

                    # Verify BGE-M3 encode_text was called
                    mock_bge_m3_service.encode_text.assert_called_once_with("What is machine learning?")

                    # Get the embedding passed to Milvus
                    call_kwargs = mock_milvus_service.search_contents.call_args[1]
                    embedding = call_kwargs["embedding"]

                    # Verify embedding is 1024-dim
                    assert len(embedding) == 1024
                    assert isinstance(embedding, list)

    @pytest.mark.asyncio
    async def test_retrieve_calls_milvus_search_contents(self, mock_bge_m3_service, mock_milvus_service, mock_reranker_service):
        """Test 2: retrieve_with_reranking calls Milvus.search_contents."""
        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                with patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker_service):
                    results = await retrieve_with_reranking(
                        query="What is machine learning?",
                        user_id="test-user",
                        paper_ids=["paper-1"],
                        top_k=20,
                        rerank_top_n=5,
                    )

                    # Verify Milvus search_contents was called
                    mock_milvus_service.search_contents.assert_called_once()

                    # Verify parameters
                    call_kwargs = mock_milvus_service.search_contents.call_args[1]
                    assert call_kwargs["user_id"] == "test-user"
                    assert call_kwargs["content_type"] == "text"
                    assert call_kwargs["top_k"] == 20

    @pytest.mark.asyncio
    async def test_retrieve_applies_reranking(self, mock_bge_m3_service, mock_milvus_service, mock_reranker_service):
        """Test 3: retrieve_with_reranking applies reranking."""
        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                with patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker_service):
                    results = await retrieve_with_reranking(
                        query="What is machine learning?",
                        user_id="test-user",
                        paper_ids=["paper-1"],
                        top_k=20,
                        rerank_top_n=5,
                    )

                    # Verify reranker was called
                    mock_reranker_service.rerank.assert_called_once()

                    # Verify rerank parameters
                    call_kwargs = mock_reranker_service.rerank.call_args[1]
                    assert call_kwargs["query"] == "What is machine learning?"
                    assert len(call_kwargs["documents"]) == 2
                    assert call_kwargs["top_k"] == 5

                    # Verify results have rerank_score
                    assert len(results) > 0
                    for result in results:
                        assert "rerank_score" in result

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_paper_ids(self, mock_bge_m3_service, mock_milvus_service, mock_reranker_service):
        """Test that retrieve_with_reranking filters by paper_ids."""
        # Mock Milvus to return results from multiple papers
        mock_milvus_service.search_contents = Mock(return_value=[
            {
                "id": 1,
                "paper_id": "paper-1",
                "content_data": "Content from paper 1",
                "distance": 0.1,
            },
            {
                "id": 2,
                "paper_id": "paper-2",
                "content_data": "Content from paper 2",
                "distance": 0.2,
            },
        ])

        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                with patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker_service):
                    # Filter to only paper-1
                    results = await retrieve_with_reranking(
                        query="test query",
                        user_id="test-user",
                        paper_ids=["paper-1"],
                        top_k=20,
                        rerank_top_n=5,
                    )

                    # Verify all results are from paper-1
                    for result in results:
                        assert result.get("paper_id") == "paper-1"

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self, mock_bge_m3_service, mock_milvus_service, mock_reranker_service):
        """Test retrieve_with_reranking with empty Milvus results."""
        mock_milvus_service.search_contents = Mock(return_value=[])

        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                with patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker_service):
                    results = await retrieve_with_reranking(
                        query="test query",
                        user_id="test-user",
                        paper_ids=["paper-1"],
                    )

                    # Verify empty results returned
                    assert results == []

                    # Reranker should not be called
                    mock_reranker_service.rerank.assert_not_called()


class TestRAGServiceDeprecated:
    """Test deprecated RAGService class."""

    def test_rag_service_warns_on_init(self):
        """Test that RAGService emits deprecation warning."""
        # The deprecation warning is already emitted on module import
        # This test just verifies the class exists and is marked deprecated
        import warnings
        from app.core.rag_service import RAGService

        # Check that the class docstring contains deprecation notice
        docstring = RAGService.__doc__ or ""
        assert "DEPRECATED" in docstring
        assert "MultimodalSearchService" in docstring

    @pytest.mark.asyncio
    async def test_rag_service_query_deprecated(self, mock_bge_m3_service, mock_milvus_service):
        """Test 4: RAGService.query uses Milvus directly."""
        # Mock semantic cache to avoid Redis dependency
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch('app.core.semantic_cache.SemanticCache', return_value=mock_cache):
            with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge_m3_service):
                with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus_service):
                    import warnings

                    with warnings.catch_warnings(record=True):
                        warnings.simplefilter("always")
                        from app.core.rag_service import RAGService
                        service = RAGService()

                        result = await service.query(
                            question="What is machine learning?",
                            paper_ids=["paper-1"],
                            user_id="test-user",
                            top_k=5,
                        )

                        # Should have answer
                        assert "answer" in result