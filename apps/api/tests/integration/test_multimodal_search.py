"""Integration tests for MultimodalSearchService.

Tests:
- Basic multimodal search functionality
- Intent detection integration
- ReRanker integration
- Paper ID filtering
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.multimodal_search_service import (
    MultimodalSearchService,
    get_multimodal_search_service,
)


class TestMultimodalSearchService:
    """Integration tests for MultimodalSearchService."""

    @pytest.fixture
    def mock_services(self):
        """Mock dependent services."""
        with patch("app.core.multimodal_search_service.get_bge_m3_service") as mock_bge, \
             patch("app.core.multimodal_search_service.get_milvus_service") as mock_milvus, \
             patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker:

            # Setup BGE mock
            bge_instance = MagicMock()
            bge_instance.encode_text.return_value = [0.1] * 1024
            mock_bge.return_value = bge_instance

            # Setup Milvus mock
            milvus_instance = MagicMock()
            milvus_instance.search_contents.return_value = [
                {
                    "id": f"test-{i}",
                    "paper_id": "paper-1",
                    "page_num": i,
                    "content_type": "text",
                    "content_data": f"content {i}",
                    "distance": 0.1,
                }
                for i in range(5)
            ]
            mock_milvus.return_value = milvus_instance

            # Setup ReRanker mock
            reranker_instance = MagicMock()
            reranker_instance.rerank.return_value = [
                ("content 0", 0.95),
                ("content 1", 0.85),
                ("content 2", 0.75),
            ]
            mock_reranker.return_value = reranker_instance

            yield {
                "bge": bge_instance,
                "milvus": milvus_instance,
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
        mock_services["milvus"].search_contents.return_value = [
            {
                "id": f"test-{i}",
                "paper_id": "paper-1",
                "page_num": i,
                "content_type": "text",
                "content_data": f"content {i}",
                "distance": 0.1,
            }
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

        # Verify results have reranker_score (only if reranking actually happened)
        if len(result_with_reranker["results"]) > 10:
            assert all(
                "reranker_score" in r
                for r in result_with_reranker["results"]
            )

    @pytest.mark.asyncio
    async def test_paper_filtering(self, mock_services):
        """Test that results are filtered by paper_ids."""
        service = MultimodalSearchService()

        # Setup Milvus to return results from multiple papers
        mock_services["milvus"].search_contents.return_value = [
            {
                "id": "test-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_type": "text",
                "content_data": "content 1",
                "distance": 0.1,
            },
            {
                "id": "test-2",
                "paper_id": "paper-2",  # Different paper
                "page_num": 2,
                "content_type": "text",
                "content_data": "content 2",
                "distance": 0.2,
            },
        ]

        # Search only for paper-1
        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        # Verify only paper-1 results returned
        for r in result["results"]:
            assert r["paper_id"] == "paper-1"

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
        mock_services["milvus"].search_contents.assert_called()
        call_kwargs = mock_services["milvus"].search_contents.call_args[1]
        assert call_kwargs["content_type"] == "image"


class TestMultimodalSearchServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_multimodal_search_service_singleton(self):
        """Test that get_multimodal_search_service returns singleton."""
        with patch("app.core.multimodal_search_service.get_bge_m3_service"), \
             patch("app.core.multimodal_search_service.get_milvus_service"), \
             patch("app.core.multimodal_search_service.get_reranker_service"):

            service1 = get_multimodal_search_service()
            service2 = get_multimodal_search_service()

            # Should return same instance
            assert service1 is service2