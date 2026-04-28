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

    assert payload["response_type"] == "rag"
    assert payload["answer_mode"] in {"full", "partial", "abstain"}
    assert "claims" in payload
    assert "citations" in payload
    assert "evidence_blocks" in payload
    assert "quality" in payload
    assert payload["trace_id"] == "trace-1"
    assert payload["run_id"]
    assert payload["retrieval_trace_id"] == "trace-1"
    assert payload["evidence_blocks"][0]["evidence_id"] == "sid-1"
    assert "citation_jump_url" in payload["evidence_blocks"][0]


def test_answer_contract_payload_honors_top_k(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])
    captured: dict[str, object] = {}

    def fake_retrieve_evidence(**kwargs):
        captured.update(kwargs)
        return schemas.EvidencePack(
            query_id="q-top-k",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id=f"sid-{index}",
                    paper_id="p-1",
                    section_id="results",
                    content_type="text",
                    anchor_text=f"statement {index}",
                    rerank_score=0.9 - (index * 0.05),
                )
                for index in range(3)
            ],
            diagnostics={},
        )

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        fake_retrieve_evidence,
    )

    payload = build_answer_contract_payload(
        query="top k test",
        user_id="u-1",
        stage="rule",
        top_k=2,
    )

    assert captured["top_k"] == 2
    assert len(payload["citations"]) == 2
    assert len(payload["evidence_blocks"]) == 2
