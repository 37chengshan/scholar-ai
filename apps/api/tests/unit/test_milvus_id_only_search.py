from __future__ import annotations

import json
from types import SimpleNamespace

from app.config import settings
from app.core.milvus_service import MilvusService
from app.models.retrieval import SearchConstraints


class _ExplodingEntityHit:
    def __init__(self, hit_id: str, distance: float) -> None:
        self.id = hit_id
        self.distance = distance

    @property
    def entity(self):
        raise AssertionError("entity should not be accessed in ID-only mode")


def test_search_contents_v2_id_only_mode_avoids_entity_decode(monkeypatch):
    service = MilvusService()
    collection = SimpleNamespace(
        name="paper_contents_v2_qwen_v2_raw_v2_1",
        schema=SimpleNamespace(
            fields=[
                SimpleNamespace(name="embedding", params={"dim": 2}),
                SimpleNamespace(name="paper_id"),
                SimpleNamespace(name="page_num"),
                SimpleNamespace(name="content_type"),
                SimpleNamespace(name="section"),
                SimpleNamespace(name="content_data"),
                SimpleNamespace(name="indexable"),
            ]
        ),
    )
    collection.search_calls = []

    def _search(**kwargs):
        collection.search_calls.append(kwargs)
        return [[_ExplodingEntityHit("chunk-1", 0.12)]]

    collection.search = _search

    monkeypatch.setenv("MILVUS_ID_ONLY_SEARCH", "1")
    monkeypatch.setattr(settings, "MILVUS_COLLECTION_CONTENTS_V2", collection.name, raising=False)
    monkeypatch.setattr(service, "get_collection", lambda _: collection)
    monkeypatch.setattr(service, "inspect_collection_vector_dim", lambda *args, **kwargs: 2)

    results = service.search_contents_v2(
        embedding=[0.1, 0.2],
        top_k=3,
        constraints=SearchConstraints(user_id="user-1", paper_ids=["paper-1"]),
    )

    assert len(results) == 1
    assert results[0]["id"] == "chunk-1"
    assert results[0]["distance"] == 0.12
    assert results[0]["paper_id"] == ""
    assert results[0]["content_data"] == ""
    assert results[0]["milvus_output_fields"] == []
    assert results[0]["milvus_search_path"] == "dense_search_primary"
    assert collection.search_calls[0]["output_fields"] == []


def test_search_contents_v2_id_only_mode_hydrates_from_artifact_store(monkeypatch, tmp_path):
    service = MilvusService()
    collection = SimpleNamespace(
        name="paper_contents_v2_qwen_v2_rule_v2_1",
        schema=SimpleNamespace(
            fields=[
                SimpleNamespace(name="embedding", params={"dim": 2}),
                SimpleNamespace(name="indexable"),
            ]
        ),
    )

    def _search(**kwargs):
        return [[_ExplodingEntityHit(42, 0.2)]]

    collection.search = _search

    hydrate_store = tmp_path / "hydrate.json"
    hydrate_store.write_text(
        json.dumps(
            {
                "collections": {
                    collection.name: {
                        "42": {
                            "source_chunk_id": "chunk-42",
                            "paper_id": "paper-42",
                            "page_num": 7,
                            "content_type": "text",
                            "section": "Results",
                            "content_data": "Hydrated evidence",
                            "quality_score": 0.91,
                        }
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MILVUS_ID_ONLY_SEARCH", "1")
    monkeypatch.setenv("MILVUS_ENTITY_HYDRATION_STORE", str(hydrate_store))
    monkeypatch.setattr(settings, "MILVUS_COLLECTION_CONTENTS_V2", collection.name, raising=False)
    monkeypatch.setattr(service, "get_collection", lambda _: collection)
    monkeypatch.setattr(service, "inspect_collection_vector_dim", lambda *args, **kwargs: 2)

    results = service.search_contents_v2(
        embedding=[0.1, 0.2],
        top_k=3,
        constraints=SearchConstraints(user_id="user-1", paper_ids=["paper-42"]),
    )

    assert len(results) == 1
    assert results[0]["id"] == 42
    assert results[0]["source_id"] == "chunk-42"
    assert results[0]["paper_id"] == "paper-42"
    assert results[0]["page_num"] == 7
    assert results[0]["content_data"] == "Hydrated evidence"


def test_search_contents_v2_id_only_mode_retry_path_avoids_entity_decode(monkeypatch):
    service = MilvusService()
    collection = SimpleNamespace(
        name="paper_contents_v2_qwen_v2_llm_v2_1",
        schema=SimpleNamespace(
            fields=[
                SimpleNamespace(name="embedding", params={"dim": 2}),
                SimpleNamespace(name="paper_id"),
                SimpleNamespace(name="page_num"),
                SimpleNamespace(name="content_type"),
                SimpleNamespace(name="section"),
                SimpleNamespace(name="content_data"),
                SimpleNamespace(name="indexable"),
            ]
        ),
    )

    collection.search_calls = []

    def _search(**kwargs):
        collection.search_calls.append(kwargs)
        if len(collection.search_calls) == 1:
            raise Exception("unsupported field type: json")
        return [[_ExplodingEntityHit("chunk-retry", 0.08)]]

    collection.search = _search

    monkeypatch.setenv("MILVUS_ID_ONLY_SEARCH", "1")
    monkeypatch.setattr(settings, "MILVUS_COLLECTION_CONTENTS_V2", collection.name, raising=False)
    monkeypatch.setattr(service, "get_collection", lambda _: collection)
    monkeypatch.setattr(service, "inspect_collection_vector_dim", lambda *args, **kwargs: 2)
    monkeypatch.setattr(service, "resolve_safe_output_fields", lambda *_args, **_kwargs: ["paper_id", "content_data"])

    results = service.search_contents_v2(
        embedding=[0.1, 0.2],
        top_k=3,
        constraints=SearchConstraints(user_id="user-1", paper_ids=["paper-1"]),
    )

    assert len(results) == 1
    assert results[0]["id"] == "chunk-retry"
    assert results[0]["milvus_search_path"] == "dense_search_minimal_retry"
    assert len(collection.search_calls) == 2
    assert collection.search_calls[0]["output_fields"] == []
    assert collection.search_calls[1]["output_fields"] == ["paper_id", "content_data"]
