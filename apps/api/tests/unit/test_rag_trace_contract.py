from __future__ import annotations

import asyncio

from app.rag_v3.main_path_service import build_answer_contract_payload
from app.services.phase6_runtime_service import build_phase6_runtime_contract


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
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="trace answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="trace this", user_id="u-1", trace_id="trace-contract-1", stage="rule"
    ))

    assert payload["retrieval_trace_id"] == "trace-contract-1"
    assert "trace" in payload
    assert payload["trace"]["trace_id"] == "trace-contract-1"
    assert "spans" in payload["trace"]
    assert "rag.request" in payload["trace"]["spans"]
    assert "cost_estimate" in payload
    assert payload["trace"]["task_family"] == "single_paper_fact"
    assert payload["trace"]["execution_mode"] == "local_evidence"
    assert payload["trace"]["phase6_runtime"]["confidence_level"] in {"high-confidence", "medium-confidence", "low-confidence"}
    assert payload["quality"]["phase6_runtime"]["answer_mode"] == payload["answer_mode"]
    assert payload["phase6_runtime"]["recovery_outcome"] in {"not_needed", "recovered", "partial", "failed"}
    assert captured["retrieval_depth"] == "shallow"
    assert captured["retrieval_model_policy"] == "flash"


def test_phase6_runtime_marks_unsurfaced_fallback_as_silent_and_low_confidence() -> None:
    contract = build_phase6_runtime_contract(
        answer_mode="full",
        degraded_conditions=["graph_unavailable"],
        recovery_actions=[],
        fallback_used=True,
        fallback_events=["graph_unavailable"],
    )

    assert contract["silent_fallback"] is True
    assert contract["confidence_level"] == "low-confidence"


def test_rag_trace_contract_surfaces_raptor_lite_signals(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q-raptor",
            query=kwargs["query"],
            query_family="compare",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-summary-1",
                    paper_id="p-1",
                    section_id="paper_summary",
                    content_type="text",
                    anchor_text="summary-backed evidence",
                    candidate_sources=["summary_index"],
                    rerank_score=0.9,
                )
            ],
            diagnostics={
                "summary_index_hits": 1.0,
                "section_candidates": 3.0,
                "retrieval_depth_rank": 2.0,
            },
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="compare answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="比较两篇论文的方法差异",
        user_id="u-1",
        trace_id="trace-raptor-1",
        query_family="compare",
        paper_scope=["p-1", "p-2"],
        stage="rule",
    ))

    assert payload["phase6_runtime"]["raptor_lite_used"] is True
    assert "paper_summary_index" in payload["phase6_runtime"]["raptor_lite_signals"]
    assert "section_summary_recall" in payload["phase6_runtime"]["raptor_lite_signals"]
    assert "deep_retrieval_plan" in payload["phase6_runtime"]["raptor_lite_signals"]


def test_rag_trace_contract_marks_runtime_fallback_events_as_fallback_used(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"]).EvidencePack(
            query_id="q-runtime-fallback",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                __import__("app.rag_v3.schemas", fromlist=["EvidenceCandidate"]).EvidenceCandidate(
                    source_chunk_id="sid-runtime-fallback-1",
                    paper_id="p-1",
                    section_id="methods",
                    content_type="text",
                    anchor_text="runtime fallback evidence",
                    rerank_score=0.81,
                )
            ],
            diagnostics={
                "runtime_truth": {
                    "fallback_events": ["embedding_provider_fallback"],
                    "degraded_conditions": ["embedding_provider_fallback"],
                }
            },
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="fact answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="这篇论文的方法是什么",
        user_id="u-1",
        trace_id="trace-runtime-fallback-1",
        query_family="fact",
        paper_scope=["p-1"],
        stage="rule",
    ))

    assert payload["phase6_runtime"]["fallback_used"] is True
    assert payload["quality"]["fallback_used"] is True
    assert payload["trace"]["fallback_used"] is True


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
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="survey answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="请做一个研究现状综述",
        user_id="u-1",
        trace_id="trace-survey-1",
        stage="rule",
    ))

    assert payload["task_family"] == "survey"
    assert payload["execution_mode"] == "local_evidence"
    assert "global_review_fallback_to_local_evidence" in payload["degraded_conditions"]
    assert payload["retrieval_plane_policy"]["requested_execution_mode"] == "global_review"
    assert payload["truthfulness_summary"]["citation_coverage"] >= 0.0
    assert "unsupported_claim_rate" in payload["trace"]["truthfulness_report_summary"]
    assert payload["phase6_runtime"]["degraded"] is True
    assert "global_review_fallback_to_local_evidence" in payload["phase6_runtime"]["degraded_reasons"]


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
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="multi survey answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="请做一个多论文研究现状综述",
        user_id="u-1",
        trace_id="trace-survey-multi-1",
        stage="rule",
        paper_scope=["p-1", "p-2"],
    ))

    assert payload["execution_mode"] == "local_evidence"
    assert payload["retrieval_plane_policy"]["requested_execution_mode"] == "global_review"
    assert "global_review_fallback_to_local_evidence" in payload["degraded_conditions"]
    assert payload["phase6_runtime"]["next_step_entry"]["entry_type"] == "read"
