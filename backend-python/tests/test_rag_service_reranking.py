"""Tests for reranking integration in retrieval flow.

Tests the retrieve_with_reranking function which:
1. Performs initial Milvus search with top_k=20
2. Calls reranker to sort results by relevance
3. Returns top 5 results with rerank_score field
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from app.core.rag_service import retrieve_with_reranking


class TestRerankingIntegration:
    """Test suite for reranking integration."""

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking_exists(self):
        """Test 1: retrieve_with_reranking() function exists."""
        # Check function exists
        from app.core import rag_service
        assert hasattr(rag_service, 'retrieve_with_reranking')
        assert callable(getattr(rag_service, 'retrieve_with_reranking'))

    @pytest.mark.asyncio
    @patch('app.core.rag_service.bge_m3_service')
    @patch('app.core.rag_service.milvus_service')
    async def test_retrieve_with_reranking_calls_initial_milvus_search(
        self, mock_milvus, mock_bge_m3
    ):
        """Test 2: Function calls initial Milvus search with top_k=20."""
        # Setup mocks
        mock_bge_m3.encode_text = Mock(return_value=[0.1] * 1024)
        mock_milvus.search_contents = Mock(return_value=[
            {"content_data": "doc1", "paper_id": "p1"},
            {"content_data": "doc2", "paper_id": "p2"},
        ])

        query = "test query"
        user_id = "user123"

        # Call function
        await retrieve_with_reranking(query=query, user_id=user_id)

        # Verify Milvus search called with top_k=20
        mock_milvus.search_contents.assert_called_once()
        call_args = mock_milvus.search_contents.call_args
        assert call_args[1]['top_k'] == 20

    @pytest.mark.asyncio
    @patch('app.core.rag_service.reranker_service')
    @patch('app.core.rag_service.bge_m3_service')
    @patch('app.core.rag_service.milvus_service')
    async def test_retrieve_with_reranking_calls_reranker(
        self, mock_milvus, mock_bge_m3, mock_reranker
    ):
        """Test 3: Function calls reranker with documents and query."""
        # Setup mocks
        mock_bge_m3.encode_text = Mock(return_value=[0.1] * 1024)
        
        mock_milvus.search_contents = Mock(return_value=[
            {"content_data": "doc1 text", "paper_id": "p1"},
            {"content_data": "doc2 text", "paper_id": "p2"},
        ])

        # Mock reranker response
        mock_reranked_result = [
            Mock(index=0, relevance_score=0.95),
            Mock(index=1, relevance_score=0.85),
        ]
        mock_reranker.rerank = Mock(return_value=mock_reranked_result)

        query = "test query"
        user_id = "user123"

        # Call function
        await retrieve_with_reranking(query=query, user_id=user_id)

        # Verify reranker called with query and documents
        mock_reranker.rerank.assert_called_once()
        call_args = mock_reranker.rerank.call_args
        assert call_args[1]['query'] == query
        assert 'doc1 text' in call_args[1]['documents']
        assert 'doc2 text' in call_args[1]['documents']

    @pytest.mark.asyncio
    @patch('app.core.rag_service.reranker_service')
    @patch('app.core.rag_service.bge_m3_service')
    @patch('app.core.rag_service.milvus_service')
    async def test_retrieve_with_reranking_returns_top_5_with_rerank_score(
        self, mock_milvus, mock_bge_m3, mock_reranker
    ):
        """Test 4: Function returns top 5 results with rerank_score field."""
        # Setup mocks
        mock_bge_m3.encode_text = Mock(return_value=[0.1] * 1024)
        
        # Create 10 initial results
        initial_results = [
            {
                "content_data": f"doc{i} text",
                "paper_id": f"p{i}",
                "page_num": i,
            }
            for i in range(10)
        ]
        mock_milvus.search_contents = Mock(return_value=initial_results)

        # Mock reranker to return top 5
        mock_reranked_result = [
            Mock(index=i, relevance_score=0.9 - i * 0.05)
            for i in range(5)
        ]
        mock_reranker.rerank = Mock(return_value=mock_reranked_result)

        query = "test query"
        user_id = "user123"

        # Call function
        results = await retrieve_with_reranking(query=query, user_id=user_id)

        # Verify top 5 returned
        assert len(results) == 5
        
        # Verify each has rerank_score field
        for result in results:
            assert "rerank_score" in result
            assert isinstance(result["rerank_score"], float)

    @pytest.mark.asyncio
    @patch('app.core.rag_service.reranker_service')
    @patch('app.core.rag_service.bge_m3_service')
    @patch('app.core.rag_service.milvus_service')
    async def test_retrieve_with_reranking_preserves_metadata(
        self, mock_milvus, mock_bge_m3, mock_reranker
    ):
        """Test 5: Function preserves original result metadata (paper_id, page_num, etc.)."""
        # Setup mocks
        mock_bge_m3.encode_text = Mock(return_value=[0.1] * 1024)
        
        initial_results = [
            {
                "content_data": "doc1 text",
                "paper_id": "paper-uuid-1",
                "page_num": 5,
                "section": "Results",
            },
            {
                "content_data": "doc2 text",
                "paper_id": "paper-uuid-2",
                "page_num": 10,
                "section": "Methods",
            },
        ]
        mock_milvus.search_contents = Mock(return_value=initial_results)

        # Mock reranker
        mock_reranked_result = [
            Mock(index=0, relevance_score=0.95),
            Mock(index=1, relevance_score=0.85),
        ]
        mock_reranker.rerank = Mock(return_value=mock_reranked_result)

        query = "test query"
        user_id = "user123"

        # Call function
        results = await retrieve_with_reranking(query=query, user_id=user_id)

        # Verify metadata preserved
        assert results[0]["paper_id"] == "paper-uuid-1"
        assert results[0]["page_num"] == 5
        assert results[0]["section"] == "Results"
        assert results[0]["rerank_score"] == 0.95

        assert results[1]["paper_id"] == "paper-uuid-2"
        assert results[1]["page_num"] == 10
        assert results[1]["section"] == "Methods"
        assert results[1]["rerank_score"] == 0.85

    @pytest.mark.asyncio
    @patch('app.core.rag_service.reranker_service')
    @patch('app.core.rag_service.bge_m3_service')
    @patch('app.core.rag_service.milvus_service')
    async def test_retrieve_with_reranking_with_paper_ids_filter(
        self, mock_milvus, mock_bge_m3, mock_reranker
    ):
        """Test 6: Function supports paper_ids filtering."""
        # Setup mocks
        mock_bge_m3.encode_text = Mock(return_value=[0.1] * 1024)
        mock_milvus.search_contents = Mock(return_value=[])
        mock_reranker.rerank = Mock(return_value=[])

        query = "test query"
        user_id = "user123"
        paper_ids = ["paper1", "paper2"]

        # Call function with paper_ids
        await retrieve_with_reranking(
            query=query,
            user_id=user_id,
            paper_ids=paper_ids
        )

        # Verify filter expression includes paper_ids
        call_args = mock_milvus.search_contents.call_args
        filter_expr = call_args[1]['filter_expr']
        assert 'paper_id' in filter_expr
        assert 'paper1' in filter_expr or 'paper2' in filter_expr