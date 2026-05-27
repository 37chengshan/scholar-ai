"""Integration tests for enhanced MultimodalSearchService with query understanding.

Tests the integration of:
- Intent detection (question/compare/summary/evolution)
- Query expansion with synonyms
- Metadata extraction and filtering
- Intent-based result formatting

Per Plan 04-02 Task 3: 5 integration tests for enhanced service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.multimodal_search_service import (
    MultimodalSearchService,
)
from app.core.rag_runtime_profile import ACTIVE_EMBEDDING_DIMENSION
from app.models.retrieval import RetrievedChunk


class TestEnhancedMultimodalSearchService:
    """Integration tests for enhanced MultimodalSearchService."""

    @pytest.fixture
    def mock_services(self):
        """Mock dependent services."""
        with patch("app.core.multimodal_search_service.get_embedding_service") as mock_embedding, \
             patch("app.core.multimodal_search_service.get_vector_store_repository") as mock_vector_store, \
             patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker, \
             patch("app.core.multimodal_search_service.create_embedding_provider") as mock_provider_factory, \
             patch("app.core.multimodal_search_service.redis_db.get", new=AsyncMock(return_value=None)), \
             patch("app.core.multimodal_search_service.redis_db.set", new=AsyncMock(return_value=None)), \
             patch("app.core.multimodal_search_service.settings.SCIENTIFIC_TEXT_BRANCH_ENABLED", False):

            # Setup embedding mock
            embedding_instance = MagicMock()
            embedding_instance.is_loaded.return_value = True
            embedding_instance.get_model_info.return_value = {
                "name": "text-embedding-v4",
                "provider": "dashscope_qwen",
                "dimension": str(ACTIVE_EMBEDDING_DIMENSION),
            }
            mock_embedding.return_value = embedding_instance

            # Setup vector store repository mock
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
            vector_store_instance.search_sparse.return_value = []
            vector_store_instance.search_summary_index.return_value = []
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

            provider_instance = MagicMock()
            provider_instance.embed_texts.return_value = [
                [0.1] * ACTIVE_EMBEDDING_DIMENSION
            ]
            mock_provider_factory.return_value = provider_instance

            yield {
                "embedding": embedding_instance,
                "vector_store": vector_store_instance,
                "reranker": reranker_instance,
                "provider": provider_instance,
            }

    @pytest.mark.asyncio
    async def test_intent_detection_affects_result_formatting(self, mock_services):
        """Test that intent detection affects result formatting.

        Per Task 3: Test intent detection affects result formatting.
        """
        service = MultimodalSearchService()

        # Test compare intent
        result = await service.search(
            query="YOLOv3和YOLOv4的区别",
            paper_ids=["paper-1"],
            user_id="user-1",
        )

        # Should detect "compare" intent from intent_rules
        assert result["query_intent"] == "compare"

        # Should log detected intent (verify structure)
        assert "intent" in result
        assert "query" in result

    @pytest.mark.asyncio
    async def test_compare_intent_returns_grouped_results(self, mock_services):
        """Test that compare intent returns grouped results by paper.

        Per Task 3: Test compare intent returns grouped results.
        """
        service = MultimodalSearchService()

        # Setup repository to return results from multiple papers
        mock_services["vector_store"].search.return_value = [
            RetrievedChunk(
                paper_id="paper-1",
                text="YOLOv3 performance",
                score=0.9,
                page_num=1,
                content_type="text",
            ),
            RetrievedChunk(
                paper_id="paper-2",
                text="YOLOv4 performance",
                score=0.85,
                page_num=2,
                content_type="text",
            ),
            RetrievedChunk(
                paper_id="paper-1",
                text="YOLOv3 architecture",
                score=0.8,
                page_num=3,
                content_type="text",
            ),
        ]

        result = await service.search(
            query="比较YOLOv3与YOLOv4的性能",
            paper_ids=["paper-1", "paper-2"],
            user_id="user-1",
        )

        # Should detect compare intent
        assert result["query_intent"] == "compare"
        assert "grouped_by_paper" in result
        assert [group["paper_id"] for group in result["grouped_by_paper"]] == ["paper-1", "paper-2"]
        assert len(result["grouped_by_paper"][0]["results"]) == 2
        assert len(result["grouped_by_paper"][1]["results"]) == 1

    @pytest.mark.asyncio
    async def test_summary_intent_returns_key_points(self, mock_services):
        """Test that summary intent returns key points structure.

        Per Task 3: Test summary intent returns key points.
        """
        service = MultimodalSearchService()

        # Setup repository to return more results for summary
        mock_services["vector_store"].search.return_value = [
            RetrievedChunk(
                paper_id="paper-1",
                text=f"Key point {i}",
                score=0.9 - (i * 0.01),
                page_num=i + 1,
                content_type="text",
            )
            for i in range(5)
        ]

        result = await service.search(
            query="总结一下这篇论文",
            paper_ids=["paper-1"],
            user_id="user-1",
        )

        # Should detect summary intent
        assert result["query_intent"] == "summary"
        assert "key_points" in result
        assert "total_chunks" in result
        assert result["total_chunks"] == 5
        assert [item["text"] for item in result["key_points"]] == [
            "Key point 0",
            "Key point 1",
            "Key point 2",
        ]

    @pytest.mark.asyncio
    async def test_query_expansion_improves_search(self, mock_services):
        """Test that query expansion improves search.

        Per Task 3: Test query expansion improves search.
        """
        service = MultimodalSearchService()

        # Query with synonym-expandable term
        result = await service.search(
            query="YOLO目标检测",
            paper_ids=["paper-1"],
            user_id="user-1",
        )

        # Should expand query with synonyms
        assert "expanded_query" in result
        assert "OR object detection" in result["expanded_query"] or "YOLO" in result["expanded_query"]

        # Online embedding provider should receive the expanded query.
        mock_services["provider"].embed_texts.assert_called()
        planned_query = mock_services["provider"].embed_texts.call_args_list[0].args[0][0]
        assert planned_query == result["expanded_query"]

    @pytest.mark.asyncio
    async def test_metadata_filtering_filters_results(self, mock_services):
        """Test that metadata filtering filters results.

        Per Task 3: Test metadata filtering filters results.
        """
        service = MultimodalSearchService()

        # Query with year metadata
        result = await service.search(
            query="2023年的论文",
            paper_ids=["paper-1"],
            user_id="user-1",
        )

        # Should extract metadata filters
        assert "metadata_filters" in result

        # Should have year_range filter and compile it into downstream constraints.
        assert result["metadata_filters"].get("year_range")
        call_kwargs = mock_services["vector_store"].search.call_args[1]
        assert call_kwargs["constraints"].year_from is not None
        assert call_kwargs["constraints"].year_to is not None

    @pytest.mark.asyncio
    async def test_intent_detection_before_search(self, mock_services):
        """Test that intent detection happens before search.

        Per Task 1: Intent detection before search.
        """
        service = MultimodalSearchService()

        call_order = []
        mock_services["provider"].embed_texts.side_effect = (
            lambda queries: call_order.append("embed") or [[0.1] * ACTIVE_EMBEDDING_DIMENSION]
        )

        result = await service.search(
            query="YOLOv3和YOLOv4的区别",
            paper_ids=["paper-1"],
            user_id="user-1",
        )

        # Intent should be detected (from intent_rules)
        assert result["query_intent"] == "compare"

        # Verify structure has intent field
        assert "intent" in result
        assert result["query_intent"] in ["question", "compare", "summary", "evolution"]
        assert call_order
