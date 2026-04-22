from unittest.mock import MagicMock, patch

import pytest

from app.models.retrieval import RetrievedChunk
from app.core.multimodal_search_service import MultimodalSearchService


@pytest.mark.asyncio
async def test_multimodal_search_narrows_constraints_with_graph_candidates() -> None:
    fake_result = RetrievedChunk(
        paper_id="paper-b",
        paper_title="Paper B",
        text="Paper B improves F1 on SQuAD over baseline BERT.",
        score=0.95,
        backend="milvus",
        source_id="chunk-1",
        page_num=2,
        section_path="Results",
        content_subtype="paragraph",
        anchor_text="improves F1 on SQuAD",
        section="Results",
        content_type="text",
    )

    with (
        patch("app.core.multimodal_search_service.get_embedding_service") as mock_embedding_factory,
        patch("app.core.multimodal_search_service.get_vector_store_repository") as mock_repo_factory,
        patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker_factory,
        patch("app.core.multimodal_search_service.build_academic_query_plan", return_value={
            "query_family": "compare",
            "planner_queries": ["Which paper improved F1 on SQuAD over baseline BERT?"],
            "expected_evidence_types": ["text"],
            "fallback_rewrites": [],
            "decontextualized_query": "Which paper improved F1 on SQuAD over baseline BERT?",
        }),
        patch("app.core.multimodal_search_service.extract_metadata_filters", return_value={}),
    ):
        embedding_service = MagicMock()
        embedding_service.encode_text.return_value = [0.1, 0.2, 0.3]
        mock_embedding_factory.return_value = embedding_service

        vector_store = MagicMock()
        vector_store.search.return_value = [fake_result]
        mock_repo_factory.return_value = vector_store
        mock_reranker_factory.return_value = MagicMock()

        service = MultimodalSearchService()
        response = await service.search(
            query="Which paper improved F1 on SQuAD over baseline BERT?",
            paper_ids=["paper-a", "paper-b"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
            content_types=["text"],
            graph_hint={"requires_graph": True, "query_family": "compare"},
            graph_candidates=[{"paper_id": "paper-b", "relation": "improves_metric_on_dataset", "score": 0.9}],
        )

    constraints = vector_store.search.call_args.kwargs["constraints"]
    assert constraints.paper_ids == ["paper-b"]
    assert response["graph_retrieval_used"] is True
    assert response["graph_candidate_count"] == 1
    assert response["graph_narrowed_paper_ids"] == ["paper-b"]
