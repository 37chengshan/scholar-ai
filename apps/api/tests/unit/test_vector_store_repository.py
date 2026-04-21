"""Tests for vector store repository read contract."""

from unittest.mock import MagicMock

from app.core.vector_store_repository import MilvusVectorStoreRepository
from app.models.retrieval import SearchConstraints


def test_milvus_repository_returns_canonical_chunks():
    milvus_service = MagicMock()
    milvus_service.search_contents_v2.return_value = [
        {
            "id": 123,
            "paper_id": "paper-1",
            "content_data": "Normalized content",
            "score": 0.88,
            "page_num": 4,
            "section": "Methods",
            "content_type": "text",
            "quality_score": 0.91,
            "raw_data": {"kind": "chunk"},
        }
    ]

    repository = MilvusVectorStoreRepository(milvus_service=milvus_service)
    constraints = SearchConstraints(user_id="user-1", paper_ids=["paper-1"])

    results = repository.search(
        embedding=[0.1] * 2048,
        user_id="user-1",
        content_type="text",
        top_k=10,
        constraints=constraints,
    )

    assert len(results) == 1
    assert results[0].paper_id == "paper-1"
    assert results[0].text == "Normalized content"
    assert results[0].score == 0.88
    assert results[0].source_id == "123"
    assert results[0].page_num == 4
    assert results[0].section == "Methods"
    assert results[0].content_type == "text"


def test_milvus_repository_forwards_search_constraints():
    milvus_service = MagicMock()
    milvus_service.search_contents_v2.return_value = []

    repository = MilvusVectorStoreRepository(milvus_service=milvus_service)
    constraints = SearchConstraints(
        user_id="user-1",
        paper_ids=["paper-1"],
        content_types=["image"],
    )

    repository.search(
        embedding=[0.1] * 2048,
        user_id="user-1",
        content_type="image",
        top_k=5,
        constraints=constraints,
    )

    milvus_service.search_contents_v2.assert_called_once_with(
        embedding=[0.1] * 2048,
        user_id="user-1",
        content_type="image",
        top_k=5,
        constraints=constraints,
    )