from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.multimodal_search_service import MultimodalSearchService


@pytest.mark.asyncio
async def test_multibranch_retrieval_exposes_branch_counts():
    with (
        patch("app.core.multimodal_search_service.get_embedding_service") as mock_embedding,
        patch("app.core.multimodal_search_service.get_vector_store_repository") as mock_vector_store,
        patch("app.core.multimodal_search_service.get_reranker_service") as mock_reranker,
        patch("app.core.multimodal_search_service.create_scientific_embedding_service") as mock_scientific,
    ):
        embedding = MagicMock()
        embedding.is_loaded.return_value = True
        embedding.encode_text.return_value = [0.1] * 2048
        mock_embedding.return_value = embedding

        vector_store = MagicMock()
        dense_hit = SimpleNamespace(
            model_dump=lambda: {
                "paper_id": "paper-1",
                "source_id": "chunk-1",
                "id": "chunk-1",
                "text": "benchmark metric table",
                "content_type": "text",
                "page_num": 1,
                "score": 0.8,
            },
            backend="milvus",
        )
        sparse_hit = SimpleNamespace(
            model_dump=lambda: {
                "paper_id": "paper-2",
                "source_id": "chunk-2",
                "id": "chunk-2",
                "text": "ablation benchmark score",
                "content_type": "text",
                "page_num": 2,
                "score": 0.6,
            }
        )
        vector_store.search.return_value = [dense_hit]
        vector_store.search_sparse.return_value = [sparse_hit]
        vector_store.search_summary_index.return_value = []
        mock_vector_store.return_value = vector_store

        reranker = MagicMock()
        reranker.is_loaded.return_value = True
        reranker.rerank.return_value = []
        mock_reranker.return_value = reranker

        scientific = MagicMock()
        scientific.generate_embedding.return_value = [0.2] * 2048
        mock_scientific.return_value = scientific

        service = MultimodalSearchService()
        response = await service.search(
            query="compare benchmark scores",
            paper_ids=["paper-1", "paper-2"],
            user_id="user-1",
            top_k=5,
            use_reranker=False,
            content_types=["text"],
        )

    assert "retrieval_branches" in response
    assert response["retrieval_branches"]["qwen_multimodal_dense"] >= 1
    assert response["retrieval_branches"]["sparse_bm25"] >= 1
    assert "query_family" in response
    assert "citation_hints" in response
    assert "summary_index_results" in response
    assert "results" in response
    assert response["results"]
