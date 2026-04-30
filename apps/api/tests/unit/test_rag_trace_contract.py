from __future__ import annotations

from app.rag_v3.main_path_service import build_answer_contract_payload


def test_rag_trace_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: captured.update(kwargs) or kwargs["stage"] and __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q-trace",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-1",
                    paper_id="p-1",
                    section_id="results",
                    content_type="text",
                    anchor_text="trace sample",
                    rerank_score=0.91,
                )
            ],
            diagnostics={},
        ),
    )

    payload = build_answer_contract_payload(
        query="trace this", user_id="u-1", trace_id="trace-contract-1", stage="rule"
    )

    assert payload["retrieval_trace_id"] == "trace-contract-1"
    assert "trace" in payload
    assert payload["trace"]["trace_id"] == "trace-contract-1"
    assert "spans" in payload["trace"]
    assert "rag.request" in payload["trace"]["spans"]
    assert "cost_estimate" in payload
    assert payload["trace"]["task_family"] == "single_paper_fact"
    assert payload["trace"]["execution_mode"] == "local_evidence"
    assert captured["retrieval_depth"] == "shallow"
    assert captured["retrieval_model_policy"] == "flash"
