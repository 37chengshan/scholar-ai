from __future__ import annotations

from app.rag_v3.main_path_service import build_answer_contract_payload


def test_answer_contract_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: kwargs["stage"] and __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q1",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-1",
                    paper_id="p-1",
                    section_id="methods",
                    content_type="text",
                    anchor_text="This is a supported statement.",
                    rerank_score=0.8,
                )
            ],
            diagnostics={},
        ),
    )

    payload = build_answer_contract_payload(
        query="test", user_id="u-1", query_family="fact", stage="rule", trace_id="trace-1"
    )

    assert payload["answer_mode"] in {"full", "partial", "abstain"}
    assert "claims" in payload
    assert "citations" in payload
    assert "evidence_blocks" in payload
    assert "quality" in payload
    assert payload["retrieval_trace_id"] == "trace-1"
