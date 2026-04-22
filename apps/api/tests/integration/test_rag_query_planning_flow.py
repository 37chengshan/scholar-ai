from unittest.mock import MagicMock, patch

import pytest

from app.core.multimodal_search_service import MultimodalSearchService
from app.models.retrieval import RetrievedChunk


@pytest.mark.asyncio
async def test_multimodal_search_exposes_planner_and_second_pass_fields():
    with (
        patch("app.core.multimodal_search_service.get_embedding_service") as mock_embedding,
        patch("app.core.multimodal_search_service.get_vector_store_repository") as mock_repo,
        patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker,
    ):
        embedding = MagicMock()
        embedding.is_loaded.return_value = True
        embedding.encode_text.return_value = [0.1] * 8
        mock_embedding.return_value = embedding

        repo = MagicMock()
        repo.search.return_value = [
            RetrievedChunk(
                paper_id="paper-a",
                text="Method A reaches 96.2 on CIFAR-10 in table 2.",
                score=0.4,
                page_num=3,
                content_type="table",
                table_ref="table-2",
                paper_role="result",
                metric_name="accuracy",
                score_value=96.2,
                evidence_bundle_id="bundle-a-1",
                evidence_types=["text", "table"],
            )
        ]
        mock_repo.return_value = repo

        reranker = MagicMock()
        reranker.is_loaded.return_value = True
        reranker.rerank.return_value = []
        mock_reranker.return_value = reranker

        service = MultimodalSearchService()
        result = await service.search(
            query="Compare method A and method B on CIFAR-10 accuracy table",
            paper_ids=["paper-a", "paper-b"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
        )

        assert result["query_family"] == "compare"
        assert result["planner_query_count"] >= 1
        assert result["decontextualized_query"]
        assert "second_pass_used" in result
        assert "second_pass_gain" in result
        assert "expected_evidence_types" in result
        assert "table" in result["expected_evidence_types"]
        assert result["results"]
        assert result["results"][0].get("evidence_bundle_id") == "bundle-a-1"
