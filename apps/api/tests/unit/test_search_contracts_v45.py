from unittest.mock import AsyncMock

import pytest

from app.api.search import V3SearchRequest, search_evidence_v3
from app.api.search.library import search_unified


@pytest.mark.asyncio
async def test_search_unified_returns_meta_and_canonical_source(monkeypatch):
    async def _fake_search_semantic_scholar(*args, **kwargs):
        return {
            "results": [
                {
                    "id": "s2-paper-1",
                    "title": "Paper One",
                    "authors": ["Author"],
                    "year": 2024,
                    "abstract": "Abstract",
                    "source": "semantic_scholar",
                    "url": "https://example.com/paper-one",
                }
            ],
            "total": 1,
        }

    monkeypatch.setattr("app.api.search.library.search_semantic_scholar", _fake_search_semantic_scholar)
    monkeypatch.setattr("app.api.search.library.get_search_cache", AsyncMock(return_value=None))
    monkeypatch.setattr("app.api.search.library.set_search_cache", AsyncMock())
    monkeypatch.setattr(
        "app.api.search.library.search_library_status_service.annotate_results",
        AsyncMock(side_effect=lambda results, **_: results),
    )

    response = await search_unified(
        query="transformer",
        source="semantic_scholar",
        limit=10,
        offset=0,
        db=AsyncMock(),
        optional_user=None,
    )

    assert response.meta == {"limit": 10, "offset": 0, "total": 1}
    assert response.data["source"] == "semantic_scholar"
    assert response.data["results"][0]["source"] == "semantic_scholar"


def test_search_evidence_v3_returns_enveloped_payload(monkeypatch) -> None:
    async def _fake_build_answer_contract_payload(**_: object) -> dict:
        return {
            "citations": [{"paper_id": "paper-1", "section_path": "Results"}],
            "evidence_blocks": [{"source_chunk_id": "chunk-1", "paper_id": "paper-1"}],
            "answer_mode": "partial",
            "quality": {},
            "trace_id": "trace-1",
        }

    import asyncio

    monkeypatch.setattr("app.api.search.build_answer_contract_payload", _fake_build_answer_contract_payload)
    payload = asyncio.run(search_evidence_v3(V3SearchRequest(query="test", top_k=5), user_id="user-1"))

    assert payload.success is True
    assert payload.data["paper_results"] == ["paper-1"]
    assert payload.data["section_matches"] == ["Results"]
    assert payload.data["retrieval_trace_id"] == "trace-1"
