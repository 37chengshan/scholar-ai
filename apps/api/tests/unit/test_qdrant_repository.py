"""Tests for Qdrant vector store repository contract."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.qdrant_mapper import QdrantMapper
from app.core.vector_store_repository import QdrantVectorStoreRepository
from app.models.retrieval import SearchConstraints


def test_qdrant_repository_returns_canonical_chunks():
    qdrant_service = MagicMock()
    qdrant_service.search.return_value = [
        {
            "id": "chunk-1",
            "paper_id": "paper-1",
            "paper_title": "Paper One",
            "text": "Qdrant normalized text",
            "score": 0.84,
            "page_num": 2,
            "section": "Results",
            "content_type": "text",
            "payload": {"section_path": "results/main"},
        }
    ]

    repository = QdrantVectorStoreRepository(qdrant_service=qdrant_service)
    constraints = SearchConstraints(user_id="user-1", paper_ids=["paper-1"])

    results = repository.search(
        embedding=[0.1] * 4,
        user_id="user-1",
        content_type="text",
        top_k=10,
        constraints=constraints,
    )

    assert len(results) == 1
    assert results[0].backend == "qdrant"
    assert results[0].source_id == "chunk-1"
    assert results[0].section_path == "results/main"


def test_qdrant_repository_forwards_constraints():
    qdrant_service = MagicMock()
    qdrant_service.search.return_value = []
    repository = QdrantVectorStoreRepository(qdrant_service=qdrant_service)
    constraints = SearchConstraints(user_id="user-1", paper_ids=["paper-1"], content_types=["table"])

    repository.search(
        embedding=[0.1] * 4,
        user_id="user-1",
        content_type="table",
        top_k=5,
        constraints=constraints,
    )

    qdrant_service.search.assert_called_once_with(
        embedding=[0.1] * 4,
        user_id="user-1",
        content_type="table",
        top_k=5,
        constraints=constraints,
    )


def test_qdrant_mapper_supports_scored_point_objects():
    record = SimpleNamespace(
        id="chunk-2",
        score=0.91,
        payload={
            "paper_id": "paper-2",
            "paper_title": "Paper Two",
            "text": "Mapped from object",
            "section_path": "discussion/closing",
            "content_type": "text",
        },
    )

    mapped = QdrantMapper.to_hit(record)

    assert mapped["id"] == "chunk-2"
    assert mapped["backend"] == "qdrant"
    assert mapped["paper_id"] == "paper-2"
    assert mapped["section_path"] == "discussion/closing"