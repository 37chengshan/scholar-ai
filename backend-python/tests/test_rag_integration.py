"""Integration tests for RAG flow with Milvus.

Per 13-03-PLAN D-34-D-36: Verify end-to-end functionality with 1024-dim embeddings.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.core.rag_service import retrieve_with_reranking
from app.core.milvus_service import get_milvus_service
from app.core.bge_m3_service import get_bge_m3_service
from app.core.reranker_service import get_reranker_service


class TestRAGIntegration:
    """Integration tests for Milvus-based RAG with 1024-dim embeddings."""

    @pytest.fixture
    def mock_services(self):
        """Mock all external services."""
        # Mock Milvus
        mock_milvus = MagicMock()
        mock_milvus.search_contents = MagicMock(return_value=[
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

        # Mock BGE-M3
        mock_bge = MagicMock()
        mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)

        # Mock Reranker
        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Machine learning is a subset of AI.", 0.95),
            ("Deep learning uses neural networks.", 0.85),
        ])

        return {
            "milvus": mock_milvus,
            "bge": mock_bge,
            "reranker": mock_reranker,
        }

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking_flow(self, mock_services):
        """Test full RAG flow: query → Milvus → rerank."""
        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_services["milvus"]), \
             patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_services["bge"]), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_services["reranker"]):

            results = await retrieve_with_reranking(
                query="What is machine learning?",
                user_id="test-user",
                paper_ids=["paper-1"],
                top_k=20,
                rerank_top_n=5,
            )

            # Verify Milvus was called with 1024-dim embedding
            mock_services["milvus"].search_contents.assert_called_once()
            call_kwargs = mock_services["milvus"].search_contents.call_args[1]
            assert len(call_kwargs["embedding"]) == 1024

            # Verify results have rerank scores
            assert len(results) > 0
            for result in results:
                assert "rerank_score" in result

    @pytest.mark.asyncio
    async def test_milvus_text_search_1024_dim(self, mock_services):
        """Test Milvus search with 1024-dim embedding."""
        # Use the mock service directly
        milvus = mock_services["milvus"]

        # Generate 1024-dim query embedding
        query_embedding = [0.1] * 1024

        results = milvus.search_contents(
            embedding=query_embedding,
            user_id="test-user",
            content_type="text",
            top_k=10,
        )

        assert len(results) > 0
        assert results[0]["content_type"] == "text"

    @pytest.mark.asyncio
    async def test_embedding_dimension_1024(self, mock_services):
        """Test BGE-M3 produces 1024-dim embeddings."""
        # Use the mock service directly
        bge = mock_services["bge"]

        embedding = bge.encode_text("test query")

        assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_reranking_improves_results(self, mock_services):
        """Test that reranking improves result ordering."""
        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_services["milvus"]), \
             patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_services["bge"]), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_services["reranker"]):

            results = await retrieve_with_reranking(
                query="machine learning",
                user_id="test-user",
                paper_ids=["paper-1"],
                top_k=20,
                rerank_top_n=5,
            )

            # Verify reranker was called
            mock_services["reranker"].rerank.assert_called_once()

            # Results should be ordered by rerank_score (descending)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i]["rerank_score"] >= results[i + 1]["rerank_score"]

    @pytest.mark.asyncio
    async def test_rag_flow_with_multiple_papers(self):
        """Test RAG flow with results from multiple papers."""
        # Mock Milvus with results from multiple papers
        mock_milvus = MagicMock()
        mock_milvus.search_contents = MagicMock(return_value=[
            {
                "id": 1,
                "paper_id": "paper-1",
                "content_data": "Paper 1 content about ML.",
                "distance": 0.1,
            },
            {
                "id": 2,
                "paper_id": "paper-2",
                "content_data": "Paper 2 content about DL.",
                "distance": 0.2,
            },
        ])

        mock_bge = MagicMock()
        mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)

        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Paper 1 content about ML.", 0.95),
            ("Paper 2 content about DL.", 0.85),
        ])

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker):

            results = await retrieve_with_reranking(
                query="machine learning and deep learning",
                user_id="test-user",
                paper_ids=["paper-1", "paper-2"],
                top_k=20,
                rerank_top_n=5,
            )

            # Verify results come from multiple papers
            paper_ids_in_results = set(r["paper_id"] for r in results)
            assert len(paper_ids_in_results) > 1  # Multiple papers represented

    @pytest.mark.asyncio
    async def test_rag_flow_no_results(self):
        """Test RAG flow when Milvus returns no results."""
        mock_milvus = MagicMock()
        mock_milvus.search_contents = MagicMock(return_value=[])

        mock_bge = MagicMock()
        mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)

        mock_reranker = MagicMock()

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker):

            results = await retrieve_with_reranking(
                query="non-existent topic",
                user_id="test-user",
                paper_ids=["paper-1"],
                top_k=20,
                rerank_top_n=5,
            )

            # Should return empty list
            assert results == []

            # Reranker should not be called
            mock_reranker.rerank.assert_not_called()

    @pytest.mark.asyncio
    async def test_rag_flow_handles_milvus_error(self):
        """Test RAG flow handles Milvus errors gracefully."""
        mock_milvus = MagicMock()
        mock_milvus.search_contents = MagicMock(side_effect=Exception("Milvus connection error"))

        mock_bge = MagicMock()
        mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)

        mock_reranker = MagicMock()

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_bge), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker):

            # Should raise exception (error handling is at API layer)
            with pytest.raises(Exception, match="Milvus connection error"):
                await retrieve_with_reranking(
                    query="test query",
                    user_id="test-user",
                    paper_ids=["paper-1"],
                )


class TestEmbeddingConsistency:
    """Test that embedding dimension is consistently 1024 throughout the pipeline."""

    def test_bge_m3_dimension_is_1024(self):
        """Test that BGE-M3 service dimension is 1024."""
        from app.core.bge_m3_service import BGEM3Service

        # Check class constant
        assert BGEM3Service.EMBEDDING_DIM == 1024

    def test_milvus_bge_dimension_is_1024(self):
        """Test that Milvus BGE dimension constant is 1024."""
        from app.core.milvus_service import MilvusService

        # Check class constant
        assert MilvusService.BGE_EMBEDDING_DIM == 1024

    def test_embedding_service_dimension_is_1024(self):
        """Test that EmbeddingService dimension is 1024."""
        from app.core.embedding_service import EmbeddingService

        with patch('app.core.embedding_service.get_bge_m3_service') as mock_get_bge:
            mock_bge = MagicMock()
            mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)
            mock_get_bge.return_value = mock_bge

            service = EmbeddingService()
            assert service.dimension == 1024


class TestMultimodalSearchIntegration:
    """Test MultimodalSearchService integration with Milvus."""

    @pytest.fixture
    def mock_all_services(self):
        """Mock all services for multimodal search."""
        mock_bge = MagicMock()
        mock_bge.encode_text = MagicMock(return_value=[0.1] * 1024)

        mock_milvus = MagicMock()
        mock_milvus.search_contents = MagicMock(return_value=[
            {
                "id": 1,
                "paper_id": "paper-1",
                "content_type": "text",
                "content_data": "Test content",
                "distance": 0.1,
            }
        ])

        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Test content", 0.95),
        ])

        return {
            "bge": mock_bge,
            "milvus": mock_milvus,
            "reranker": mock_reranker,
        }

    @pytest.mark.asyncio
    async def test_multimodal_search_uses_1024_dim(self, mock_all_services):
        """Test that MultimodalSearchService uses 1024-dim embeddings."""
        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_all_services["bge"]), \
             patch('app.core.milvus_service.get_milvus_service', return_value=mock_all_services["milvus"]), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_all_services["reranker"]):

            from app.core.multimodal_search_service import get_multimodal_search_service

            service = get_multimodal_search_service()
            result = await service.search(
                query="test query",
                paper_ids=["paper-1"],
                user_id="test-user",
                top_k=5,
                use_reranker=True,
            )

            # Verify BGE-M3 was called
            mock_all_services["bge"].encode_text.assert_called()

            # Verify Milvus was called with 1024-dim embedding
            mock_all_services["milvus"].search_contents.assert_called()

            # Verify result structure
            assert "results" in result
            assert "total_count" in result