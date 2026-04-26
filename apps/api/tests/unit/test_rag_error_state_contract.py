from __future__ import annotations

from app.rag_v3.main_path_service import build_answer_contract_payload


def _pack_with(diagnostics: dict):
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])
    return schemas.EvidencePack(
        query_id="q-err",
        query="x",
        query_family="fact",
        stage="rule",
        candidates=[
            schemas.EvidenceCandidate(
                source_chunk_id="sid-1",
                paper_id="p-1",
                section_id="methods",
                content_type="text",
                anchor_text="fallback sample",
                rerank_score=0.5,
            )
        ],
        diagnostics=diagnostics,
    )


def test_error_state_fallback_used(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: _pack_with({"dense_fallback_used": 1.0}),
    )

    payload = build_answer_contract_payload(query="x", user_id="u-1", stage="rule")

    assert payload["quality"]["fallback_used"] is True
    assert payload["error_state"] in {"fallback_used", "partial_answer", "abstain"}


def test_error_state_contains_contract_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: _pack_with({}),
    )

    payload = build_answer_contract_payload(query="x", user_id="u-1", stage="rule")

    assert "error_state" in payload
    assert "quality" in payload
    assert "fallback_reason" in payload["quality"]
