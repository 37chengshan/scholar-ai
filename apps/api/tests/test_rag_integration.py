"""Integration tests for RAG flow with Milvus.

This file covers two different surfaces:
- the deprecated compatibility shim in ``app.legacy.rag_service_deprecated``
- the active online-first retrieval runtime contract
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.legacy.rag_service_deprecated import retrieve_with_reranking
from app.core.rag_runtime_profile import ACTIVE_EMBEDDING_DIMENSION


class TestRAGIntegration:
    """Integration tests for the deprecated Milvus-based compatibility shim."""

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

        # The deprecated shim still imports the local Qwen3VL service directly.
        mock_embedding = MagicMock()
        mock_embedding.encode_text = MagicMock(return_value=[0.1] * 1024)

        # Mock Reranker
        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Machine learning is a subset of AI.", 0.95),
            ("Deep learning uses neural networks.", 0.85),
        ])

        return {
            "milvus": mock_milvus,
            "embedding": mock_embedding,
            "reranker": mock_reranker,
        }

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking_flow(self, mock_services):
        """Test full RAG flow: query → Milvus → rerank."""
        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_services["milvus"]), \
             patch('app.core.qwen3vl_service.get_qwen3vl_service', return_value=mock_services["embedding"]), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_services["reranker"]):

            results = await retrieve_with_reranking(
                query="What is machine learning?",
                user_id="test-user",
                paper_ids=["paper-1"],
                top_k=20,
                rerank_top_n=5,
            )

            # The compatibility shim still passes a single query vector to Milvus.
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
        """Test mocked query embedding shape stays aligned to the runtime dim."""
        # Use the mock service directly
        embedding = mock_services["embedding"]

        vector = embedding.encode_text("test query")

        assert len(vector) == ACTIVE_EMBEDDING_DIMENSION

    @pytest.mark.asyncio
    async def test_reranking_improves_results(self, mock_services):
        """Test that reranking improves result ordering."""
        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_services["milvus"]), \
             patch('app.core.qwen3vl_service.get_qwen3vl_service', return_value=mock_services["embedding"]), \
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

        mock_embedding = MagicMock()
        mock_embedding.encode_text = MagicMock(return_value=[0.1] * ACTIVE_EMBEDDING_DIMENSION)

        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Paper 1 content about ML.", 0.95),
            ("Paper 2 content about DL.", 0.85),
        ])

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.qwen3vl_service.get_qwen3vl_service', return_value=mock_embedding), \
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

        mock_embedding = MagicMock()
        mock_embedding.encode_text = MagicMock(return_value=[0.1] * ACTIVE_EMBEDDING_DIMENSION)

        mock_reranker = MagicMock()

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.qwen3vl_service.get_qwen3vl_service', return_value=mock_embedding), \
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

        mock_embedding = MagicMock()
        mock_embedding.encode_text = MagicMock(return_value=[0.1] * ACTIVE_EMBEDDING_DIMENSION)

        mock_reranker = MagicMock()

        with patch('app.core.milvus_service.get_milvus_service', return_value=mock_milvus), \
             patch('app.core.qwen3vl_service.get_qwen3vl_service', return_value=mock_embedding), \
             patch('app.core.reranker_service.get_reranker_service', return_value=mock_reranker):

            # Should raise exception (error handling is at API layer)
            with pytest.raises(Exception, match="Milvus connection error"):
                await retrieve_with_reranking(
                    query="test query",
                    user_id="test-user",
                    paper_ids=["paper-1"],
                )


class TestEmbeddingConsistency:
    """Test the active online embedding contract stays stable."""

    def test_runtime_profile_dimension_is_1024(self):
        """The official online-first runtime stays on 1024-d embeddings."""
        assert ACTIVE_EMBEDDING_DIMENSION == 1024

    def test_milvus_dimension_matches_active_runtime(self):
        """Milvus should resolve dimension from the active embedding model."""
        from app.core.milvus_service import MilvusService

        service = MilvusService()
        assert service.embedding_dim == ACTIVE_EMBEDDING_DIMENSION

    def test_embedding_factory_dimension_is_1024(self):
        """The configured embedding factory should report the active runtime dim."""
        from app.core.embedding.factory import get_embedding_service

        service = get_embedding_service()
        info = service.get_model_info()

        assert int(info["dimension"]) == ACTIVE_EMBEDDING_DIMENSION


class TestMultimodalSearchIntegration:
    """Test MultimodalSearchService integration with Milvus."""

    @pytest.fixture
    def mock_all_services(self):
        """Mock all services for multimodal search."""
        mock_embedding = MagicMock()
        mock_embedding.encode_text = MagicMock(return_value=[0.1] * ACTIVE_EMBEDDING_DIMENSION)
        mock_embedding.is_loaded = MagicMock(return_value=True)
        mock_embedding.get_model_info = MagicMock(return_value={
            "name": "text-embedding-v4",
            "provider": "dashscope_qwen",
            "dimension": str(ACTIVE_EMBEDDING_DIMENSION),
        })
        mock_embedding.supports_multimodal = MagicMock(return_value=False)

        mock_vector_store = MagicMock()
        mock_hit = MagicMock()
        mock_hit.backend = "milvus"
        mock_hit.model_dump = MagicMock(return_value={
            "paper_id": "paper-1",
            "source_id": "chunk-1",
            "page_num": 1,
            "content_type": "text",
            "content_data": "Test content",
            "distance": 0.1,
            "score": 0.9,
        })
        mock_vector_store.search = MagicMock(return_value=[mock_hit])
        mock_vector_store.search_sparse = MagicMock(return_value=[])
        mock_vector_store.search_summary_index = MagicMock(return_value=[])

        mock_reranker = MagicMock()
        mock_reranker.rerank = MagicMock(return_value=[
            ("Test content", 0.95),
        ])
        mock_reranker.is_loaded = MagicMock(return_value=True)

        mock_provider = MagicMock()
        mock_provider.embed_texts = MagicMock(
            return_value=[[0.1] * ACTIVE_EMBEDDING_DIMENSION]
        )

        return {
            "embedding": mock_embedding,
            "vector_store": mock_vector_store,
            "reranker": mock_reranker,
            "provider": mock_provider,
        }

    @pytest.mark.asyncio
    async def test_multimodal_search_uses_1024_dim(self, mock_all_services):
        """Test that MultimodalSearchService uses 1024-dim embeddings."""
        with patch('app.core.multimodal_search_service.get_embedding_service', return_value=mock_all_services["embedding"]), \
             patch('app.core.multimodal_search_service.get_vector_store_repository', return_value=mock_all_services["vector_store"]), \
             patch('app.core.multimodal_search_service.get_reranker_service', return_value=mock_all_services["reranker"]), \
             patch('app.core.multimodal_search_service.create_embedding_provider', return_value=mock_all_services["provider"]), \
             patch('app.core.multimodal_search_service.redis_db.get', new=AsyncMock(return_value=None)), \
             patch('app.core.multimodal_search_service.redis_db.set', new=AsyncMock(return_value=None)), \
             patch('app.core.multimodal_search_service.settings.SCIENTIFIC_TEXT_BRANCH_ENABLED', False), \
             patch('app.core.multimodal_search_service._multimodal_search_service', None):

            from app.core.multimodal_search_service import get_multimodal_search_service

            service = get_multimodal_search_service()
            result = await service.search(
                query="test query",
                paper_ids=["paper-1"],
                user_id="test-user",
                top_k=5,
                use_reranker=True,
            )

            # Verify the online embedding provider was used.
            mock_all_services["provider"].embed_texts.assert_called()

            # Verify vector store search received a 1024-dim query vector.
            mock_all_services["vector_store"].search.assert_called()
            first_call = mock_all_services["vector_store"].search.call_args_list[0]
            assert len(first_call.kwargs["embedding"]) == ACTIVE_EMBEDDING_DIMENSION

            # Verify result structure
            assert "results" in result
            assert "total_count" in result
