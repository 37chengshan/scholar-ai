"""Integration smoke tests for the Qdrant retrieval adapter.

These tests exercise the Qdrant service and repository boundary together so the
Qdrant comparison round has a minimal executable entry point even when no real
Qdrant server is available in CI.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.config import settings
from app.core.qdrant_service import QdrantService
from app.core.vector_store_repository import QdrantVectorStoreRepository
from app.models.retrieval import SearchConstraints


def test_qdrant_service_search_maps_hits_and_forwards_filters():
    fake_client = MagicMock()
    fake_client.search.return_value = [
        SimpleNamespace(
            id="chunk-1",
            score=0.87,
            payload={
                "paper_id": "paper-1",
                "paper_title": "Paper One",
                "text": "Qdrant search text",
                "page_num": 3,
                "section": "Discussion",
                "content_type": "text",
                "section_path": "discussion/results",
            },
        )
    ]

    service = QdrantService(client=fake_client)
    constraints = SearchConstraints(
        user_id="user-1",
        paper_ids=["paper-1"],
        content_types=["text"],
        year_from=2020,
        min_quality_score=0.6,
    )

    results = service.search(
        embedding=[0.1, 0.2, 0.3, 0.4],
        user_id="user-1",
        content_type="text",
        top_k=5,
        constraints=constraints,
    )

    fake_client.search.assert_called_once()
    search_kwargs = fake_client.search.call_args.kwargs
    assert search_kwargs["collection_name"] == "paper_contents_v2"
    assert search_kwargs["query_vector"] == [0.1, 0.2, 0.3, 0.4]
    assert search_kwargs["limit"] == 5
    assert search_kwargs["with_payload"] is True
    assert search_kwargs["query_filter"] == {
        "must": [
            {"key": "user_id", "match": {"value": "user-1"}},
            {"key": "paper_id", "match": {"any": ["paper-1"]}},
            {"key": "content_type", "match": {"any": ["text"]}},
            {"key": "year", "range": {"gte": 2020}},
            {"key": "quality_score", "range": {"gte": 0.6}},
        ]
    }

    assert len(results) == 1
    assert results[0]["backend"] == "qdrant"
    assert results[0]["paper_id"] == "paper-1"
    assert results[0]["section_path"] == "discussion/results"
    assert results[0]["text"] == "Qdrant search text"


def test_qdrant_repository_returns_canonical_chunks():
    fake_client = MagicMock()
    fake_client.search.return_value = [
        {
            "id": "chunk-2",
            "score": 0.91,
            "payload": {
                "paper_id": "paper-2",
                "paper_title": "Paper Two",
                "text": "Repository smoke text",
                "page_num": 9,
                "section_path": "results/closing",
                "content_type": "text",
            },
        }
    ]

    repository = QdrantVectorStoreRepository(qdrant_service=QdrantService(client=fake_client))
    constraints = SearchConstraints(user_id="user-2", paper_ids=["paper-2"])

    results = repository.search(
        embedding=[0.5, 0.4, 0.3, 0.2],
        user_id="user-2",
        content_type="text",
        top_k=3,
        constraints=constraints,
    )

    assert len(results) == 1
    assert results[0].backend == "qdrant"
    assert results[0].source_id == "chunk-2"
    assert results[0].section_path == "results/closing"
    assert results[0].text == "Repository smoke text"


def test_qdrant_service_local_mode_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "QDRANT_URL", "")
    monkeypatch.setattr(settings, "QDRANT_LOCAL_PATH", str(Path(tmp_path) / "qdrant-local"))
    monkeypatch.setattr(settings, "QDRANT_COLLECTION_CONTENTS_V2", "paper_contents_v2_test")

    service = QdrantService()
    service.ensure_collection(vector_size=4)
    inserted_ids = service.upsert_contents_batched(
        [
            {
                "id": "chunk-local-1",
                "paper_id": "paper-local-1",
                "paper_title": "Local Paper",
                "user_id": "user-local-1",
                "content_type": "text",
                "page_num": 1,
                "section": "Abstract",
                "text": "Qdrant local mode stores benchmark content",
                "content_data": "Qdrant local mode stores benchmark content",
                "raw_data": {"source": "test"},
                "embedding": [0.1, 0.2, 0.3, 0.4],
            }
        ]
    )

    results = service.search(
        embedding=[0.1, 0.2, 0.3, 0.4],
        user_id="user-local-1",
        content_type="text",
        top_k=3,
        constraints=SearchConstraints(user_id="user-local-1", paper_ids=["paper-local-1"]),
    )

    assert len(inserted_ids) == 1
    assert len(results) == 1
    assert results[0]["id"] == "chunk-local-1"
    assert results[0]["paper_id"] == "paper-local-1"
    assert results[0]["text"] == "Qdrant local mode stores benchmark content"
