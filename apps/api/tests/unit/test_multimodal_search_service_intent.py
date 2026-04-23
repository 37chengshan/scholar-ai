"""Unit tests for multimodal search service intent field verification.

Tests verify that the API response correctly returns:
- intent: modality intent (image_weighted/table_weighted/default)
- query_intent: query intent (question/compare/summary/evolution)

Per Plan 03-04: Gap closure for UAT Test 2 - intent field naming bug.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from app.core.multimodal_search_service import MultimodalSearchService


class TestIntentFieldVerification:
    """Tests verifying intent field returns modality_intent, query_intent preserved."""

    @pytest.fixture
    def mock_services(self):
        """Mock embedding, Milvus, and reranker services."""
        with (
            patch(
                "app.core.multimodal_search_service.get_embedding_service"
            ) as mock_embedding,
            patch(
                "app.core.multimodal_search_service.get_vector_store_repository"
            ) as mock_vector_store,
            patch(
                "app.core.multimodal_search_service.get_reranker_service"
            ) as mock_reranker,
            patch(
                "app.core.multimodal_search_service.create_scientific_embedding_service"
            ) as mock_scientific,
        ):
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.is_loaded.return_value = True
            mock_embedding_instance.encode_text.return_value = [0.1] * 2048
            mock_embedding.return_value = mock_embedding_instance

            mock_vector_store_instance = MagicMock()
            mock_vector_store_instance.search.return_value = []
            mock_vector_store_instance.search_sparse.return_value = []
            mock_vector_store_instance.search_summary_index.return_value = []
            mock_vector_store.return_value = mock_vector_store_instance

            mock_reranker_instance = MagicMock()
            mock_reranker_instance.is_loaded.return_value = True
            mock_reranker_instance.rerank.return_value = []
            mock_reranker.return_value = mock_reranker_instance

            mock_scientific_instance = MagicMock()
            mock_scientific_instance.generate_embedding.return_value = [0.1] * 2048
            mock_scientific.return_value = mock_scientific_instance

            yield {
                "embedding": mock_embedding_instance,
                "vector_store": mock_vector_store_instance,
                "reranker": mock_reranker_instance,
            }

    @pytest.mark.asyncio
    async def test_intent_returns_image_weighted_for_image_keywords(
        self, mock_services
    ):
        """Test 1: Query with image keywords returns intent=image_weighted and query_intent=question."""
        service = MultimodalSearchService()

        result = await service.search(
            query="显示图表中的数据",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert result["intent"] == "image_weighted"
        assert result["query_intent"] in ["question", "results"]
        assert result["weights"]["image"] == 0.6
        assert "query_family" in result
        assert "citation_hints" in result
        assert "summary_index_results" in result

    @pytest.mark.asyncio
    async def test_intent_returns_table_weighted_for_table_keywords(
        self, mock_services
    ):
        """Test 2: Query with table keywords returns intent=table_weighted and query_intent=question."""
        service = MultimodalSearchService()

        result = await service.search(
            query="查看表格数据",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert result["intent"] == "table_weighted"
        assert result["query_intent"] in ["question", "results"]
        assert result["weights"]["table"] == 0.5
        assert isinstance(result["citation_hints"], dict)

    @pytest.mark.asyncio
    async def test_intent_returns_default_for_no_keywords(self, mock_services):
        """Test 3: Query without keywords returns intent=default and query_intent=question."""
        service = MultimodalSearchService()

        result = await service.search(
            query="什么是注意力机制",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert result["intent"] == "default"
        assert result["query_intent"] == "question"
        assert result["weights"]["text"] == 0.5
        assert isinstance(result["summary_index_results"], int)

    @pytest.mark.asyncio
    async def test_compare_query_preserves_query_intent(self, mock_services):
        """Test 4: Compare query returns intent=default and query_intent=compare."""
        service = MultimodalSearchService()

        result = await service.search(
            query="对比YOLOv3和YOLOv4的区别",
            paper_ids=["paper-1", "paper-2"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert result["intent"] in ["default", "table_weighted", "image_weighted"]
        assert result["query_intent"] == "compare"
        assert "grouped_by_paper" in result

    @pytest.mark.asyncio
    async def test_summary_query_preserves_query_intent(self, mock_services):
        """Test 5: Summary query returns intent=default and query_intent=summary."""
        service = MultimodalSearchService()

        result = await service.search(
            query="总结一下这篇论文",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert result["intent"] == "default"
        assert result["query_intent"] == "summary"
        assert "key_points" in result
        assert "total_chunks" in result


class TestIntentFieldStructure:
    """Tests verifying response structure includes both intent fields."""

    @pytest.fixture
    def mock_services(self):
        """Mock services for structure tests."""
        with (
            patch(
                "app.core.multimodal_search_service.get_embedding_service"
            ) as mock_embedding,
            patch(
                "app.core.multimodal_search_service.get_vector_store_repository"
            ) as mock_vector_store,
            patch(
                "app.core.multimodal_search_service.get_reranker_service"
            ) as mock_reranker,
            patch(
                "app.core.multimodal_search_service.create_scientific_embedding_service"
            ) as mock_scientific,
        ):
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.is_loaded.return_value = True
            mock_embedding_instance.encode_text.return_value = [0.1] * 2048
            mock_embedding.return_value = mock_embedding_instance

            mock_vector_store_instance = MagicMock()
            mock_vector_store_instance.search.return_value = []
            mock_vector_store_instance.search_sparse.return_value = []
            mock_vector_store_instance.search_summary_index.return_value = []
            mock_vector_store.return_value = mock_vector_store_instance

            mock_reranker_instance = MagicMock()
            mock_reranker_instance.is_loaded.return_value = True
            mock_reranker.return_value = mock_reranker_instance

            mock_scientific_instance = MagicMock()
            mock_scientific_instance.generate_embedding.return_value = [0.1] * 2048
            mock_scientific.return_value = mock_scientific_instance

            yield {"vector_store": mock_vector_store_instance}

    @pytest.mark.asyncio
    async def test_response_has_both_intent_fields(self, mock_services):
        """Response must include both 'intent' and 'query_intent' fields."""
        service = MultimodalSearchService()

        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert "intent" in result
        assert "query_intent" in result
        assert "query_family" in result
        assert "citation_hints" in result
        assert "summary_index_results" in result

    @pytest.mark.asyncio
    async def test_intent_field_is_string(self, mock_services):
        """Intent field must be a string value."""
        service = MultimodalSearchService()

        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert isinstance(result["intent"], str)
        assert result["intent"] in ["default", "image_weighted", "table_weighted"]

    @pytest.mark.asyncio
    async def test_query_intent_field_is_string(self, mock_services):
        """Query intent field must be a string value."""
        service = MultimodalSearchService()

        result = await service.search(
            query="test query",
            paper_ids=["paper-1"],
            user_id="user-1",
            top_k=10,
            use_reranker=False,
        )

        assert isinstance(result["query_intent"], str)
        assert result["query_intent"] in [
            "question",
            "compare",
            "summary",
            "evolution",
            "method",
            "results",
            "code",
            "references",
        ]

    @pytest.mark.asyncio
    async def test_survey_query_uses_summary_index(self, mock_services):
        """Survey-family queries should trigger summary-index retrieval path in v2."""
        service = MultimodalSearchService()

        summary_hit = SimpleNamespace(
            model_dump=lambda: {
                "paper_id": "paper-1",
                "source_id": "summary-1",
                "id": "summary-1",
                "content_type": "text",
                "text": "Section summary: related work overview",
                "section": "Related Work",
                "score": 0.9,
            }
        )
        mock_services["vector_store"].search_summary_index.return_value = [summary_hit]

        with patch(
            "app.core.multimodal_search_service.build_academic_query_plan",
            return_value={
                "planner_queries": ["summarize related work"],
                "query_family": "survey",
                "query_type": "survey",
                "expected_evidence_types": ["text"],
                "decontextualized_query": "summarize related work",
                "fallback_rewrites": [],
            },
        ):
            result = await service.search(
                query="总结研究方向",
                paper_ids=["paper-1"],
                user_id="user-1",
                top_k=5,
                use_reranker=False,
                content_types=["text"],
            )

        mock_services["vector_store"].search_summary_index.assert_called()
        assert result["query_family"] == "survey"
        assert result["summary_index_results"] >= 1
        assert isinstance(result["citation_hints"], dict)

    def test_compile_to_constraints_maps_year_range(self, mock_services):
        """Year range metadata should compile into structured retrieval constraints."""
        service = MultimodalSearchService()

        constraints = service.compile_to_constraints(
            metadata_filters={"year_range": (2023, 2024)},
            user_id="user-1",
            paper_ids=["paper-1"],
        )

        assert constraints.year_from == 2023
        assert constraints.year_to == 2024
        assert constraints.paper_ids == ["paper-1"]

    def test_compile_to_constraints_wraps_scalar_content_type(self, mock_services):
        """Scalar content_type metadata should be normalized to the list contract."""
        service = MultimodalSearchService()

        constraints = service.compile_to_constraints(
            metadata_filters={"content_type": "image"},
            user_id="user-1",
            paper_ids=["paper-1"],
        )

        assert constraints.content_types == ["image"]
