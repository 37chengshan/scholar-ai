"""Integration tests for MultimodalSearchService.

Tests:
- Basic multimodal search functionality
- Intent detection integration
- ReRanker integration
- Paper ID filtering
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.multimodal_search_service import (
    MultimodalSearchService,
    get_multimodal_search_service,
)
from app.models.retrieval import RetrievedChunk


class TestMultimodalSearchService:
    """Integration tests for MultimodalSearchService."""

    @pytest.fixture
    def mock_services(self):
        """Mock dependent services."""
        with patch("app.core.multimodal_search_service.get_embedding_service") as mock_embedding, \
             patch("app.core.multimodal_search_service.get_vector_store_repository") as mock_vector_store, \
             patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker:

            # Setup embedding mock
            embedding_instance = MagicMock()
            embedding_instance.is_loaded.return_value = True
            embedding_instance.encode_text.return_value = [0.1] * 2048
            mock_embedding.return_value = embedding_instance

            # Setup repository mock
            vector_store_instance = MagicMock()
            vector_store_instance.search.return_value = [
                RetrievedChunk(
                    paper_id="paper-1",
                    text=f"content {i}",
                    score=0.9 - (i * 0.01),
                    page_num=i + 1,
                    content_type="text",
                )
                for i in range(5)
            ]
            mock_vector_store.return_value = vector_store_instance

            # Setup ReRanker mock
            reranker_instance = MagicMock()
            reranker_instance.is_loaded.return_value = True
            reranker_instance.rerank.return_value = [
                {"document": "content 0", "score": 0.95, "rank": 0},
                {"document": "content 1", "score": 0.85, "rank": 1},
                {"document": "content 2", "score": 0.75, "rank": 2},
            ]
            mock_reranker.return_value = reranker_instance

            yield {
                "embedding": embedding_instance,
                "vector_store": vector_store_instance,
                "reranker": reranker_instance,
            }

    @pytest.mark.asyncio
    async def test_multimodal_search_basic(self, mock_services):
        """Test basic multimodal search returns results."""
        service = MultimodalSearchService()

        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        # Verify structure
        assert "query" in result
        assert "intent" in result
        assert "weights" in result
        assert "results" in result
        assert "total_count" in result

        # Verify query preserved
        assert result["query"] == "test query"

        # Verify intent detected
        assert result["intent"] in ["default", "image_weighted", "table_weighted"]

        # Verify results returned
        assert isinstance(result["results"], list)
        assert result["total_count"] >= 0

    @pytest.mark.asyncio
    async def test_intent_detection_integration(self, mock_services):
        """Test that intent detection affects search behavior."""
        service = MultimodalSearchService()

        # Query with image keyword
        result = await service.search(
            query="show me the figure",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        # Should detect image intent
        assert result["intent"] == "image_weighted"
        assert result["weights"]["image"] == 0.6

        # Query with table keyword
        result = await service.search(
            query="performance table",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        # Should detect table intent
        assert result["intent"] == "table_weighted"
        assert result["weights"]["table"] == 0.5

    @pytest.mark.asyncio
    async def test_reranker_integration(self, mock_services):
        """Test that ReRanker improves results when enabled."""
        service = MultimodalSearchService()

        # Setup Milvus to return more than 10 results to trigger reranking
        mock_services["vector_store"].search.return_value = [
            RetrievedChunk(
                paper_id="paper-1",
                text=f"content {i}",
                score=0.9 - (i * 0.01),
                page_num=i + 1,
                content_type="text",
            )
            for i in range(15)  # 15 results to trigger reranking
        ]

        # With reranker enabled
        result_with_reranker = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=True,
        )

        # Verify reranker was called
        mock_services["reranker"].rerank.assert_called()

        rerank_call_args = mock_services["reranker"].rerank.call_args[0]
        assert rerank_call_args[0] == "test query"
        assert rerank_call_args[1][0].startswith("title: ")
        assert "text: content 0" in rerank_call_args[1][0]

        # Verify reranker ordering affects the returned result order.
        assert result_with_reranker["results"][0]["text"] == "content 0"

    @pytest.mark.asyncio
    async def test_paper_filtering(self, mock_services):
        """Test that paper_ids are pushed down and returned results stay scoped."""
        service = MultimodalSearchService()

        # Setup Milvus to return results from multiple papers
        all_hits = [
            RetrievedChunk(
                paper_id="paper-1",
                text="content 1",
                score=0.9,
                page_num=1,
                content_type="text",
            ),
            RetrievedChunk(
                paper_id="paper-2",
                text="content 2",
                score=0.8,
                page_num=2,
                content_type="text",
            ),
        ]

        def vector_store_search_side_effect(*args, **kwargs):
            constraints = kwargs["constraints"]
            return [
                hit for hit in all_hits if hit.paper_id in constraints.paper_ids
            ]

        mock_services["vector_store"].search.side_effect = vector_store_search_side_effect

        # Search only for paper-1
        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        # Verify paper_ids were pushed down to Milvus constraints.
        call_kwargs = mock_services["vector_store"].search.call_args[1]
        assert call_kwargs["constraints"].paper_ids == ["paper-1"]
        assert all(item["paper_id"] == "paper-1" for item in result["results"])

    @pytest.mark.asyncio
    async def test_content_type_filtering(self, mock_services):
        """Test search with specific content types."""
        service = MultimodalSearchService()

        # Search only images
        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
            content_types=["image"],
        )

        # Verify Milvus called with image content_type
        mock_services["vector_store"].search.assert_called()
        call_kwargs = mock_services["vector_store"].search.call_args[1]
        assert call_kwargs["content_type"] == "image"


class TestMultimodalSearchServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_multimodal_search_service_singleton(self):
        """Test that get_multimodal_search_service returns singleton."""
        with patch("app.core.multimodal_search_service.get_embedding_service"), \
             patch("app.core.multimodal_search_service.get_vector_store_repository"), \
             patch("app.core.multimodal_search_service.get_reranker_service"):

            service1 = get_multimodal_search_service()
            service2 = get_multimodal_search_service()

            # Should return same instance
            assert service1 is service2