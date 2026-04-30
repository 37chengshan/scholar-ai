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


def test_rag_trace_contract_honestly_degrades_global_review_to_local_execution(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q-survey",
            query=kwargs["query"],
            query_family="survey",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-survey-1",
                    paper_id="p-1",
                    section_id="introduction",
                    content_type="text",
                    anchor_text="survey sample",
                    rerank_score=0.8,
                )
            ],
            diagnostics={},
        ),
    )

    payload = build_answer_contract_payload(
        query="请做一个研究现状综述",
        user_id="u-1",
        trace_id="trace-survey-1",
        stage="rule",
    )

    assert payload["task_family"] == "survey"
    assert payload["execution_mode"] == "local_evidence"
    assert "global_review_fallback_to_local_evidence" in payload["degraded_conditions"]
    assert payload["retrieval_plane_policy"]["requested_execution_mode"] == "global_review"
    assert payload["truthfulness_summary"]["citation_coverage"] >= 0.0
    assert "unsupported_claim_rate" in payload["trace"]["truthfulness_report_summary"]


def test_rag_trace_contract_keeps_multi_paper_global_review_fallback_as_local_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q-survey-multi",
            query=kwargs["query"],
            query_family="survey",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-survey-multi-1",
                    paper_id="p-1",
                    section_id="introduction",
                    content_type="text",
                    anchor_text="survey sample",
                    rerank_score=0.8,
                ),
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-survey-multi-2",
                    paper_id="p-2",
                    section_id="background",
                    content_type="text",
                    anchor_text="survey sample 2",
                    rerank_score=0.79,
                ),
            ],
            diagnostics={},
        ),
    )

    payload = build_answer_contract_payload(
        query="请做一个多论文研究现状综述",
        user_id="u-1",
        trace_id="trace-survey-multi-1",
        stage="rule",
        paper_scope=["p-1", "p-2"],
    )

    assert payload["execution_mode"] == "local_evidence"
    assert payload["retrieval_plane_policy"]["requested_execution_mode"] == "global_review"
    assert "global_review_fallback_to_local_evidence" in payload["degraded_conditions"]
