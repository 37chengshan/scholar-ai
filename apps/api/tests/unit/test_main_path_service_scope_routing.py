from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.rag_v3.main_path_service import build_answer_contract_payload, retrieve_evidence
from app.rag_v3.schemas import EvidenceCandidate, EvidencePack


class _CapturingRetriever:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def retrieve_evidence(self, **kwargs) -> EvidencePack:
        self.kwargs = kwargs
        return EvidencePack(
            query_id="q-scope",
            query=str(kwargs["query"]),
            query_family="fact",
            stage=str(kwargs["stage"]),
            candidates=[
                EvidenceCandidate(
                    source_chunk_id="chunk-1",
                    paper_id="paper-1",
                    section_id="intro",
                    content_type="text",
                    anchor_text="scoped evidence",
                    rerank_score=0.91,
                )
            ],
            diagnostics={},
        )


def test_main_path_retrieve_evidence_forwards_explicit_paper_scope(monkeypatch) -> None:
    retriever = _CapturingRetriever()
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._get_retriever",
        lambda stage, embedding_model: retriever,
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.create_embedding_provider",
        lambda provider, model: type(
            "Provider",
            (),
            {
                "dim": 1024,
                "embed_texts": lambda self, texts: [[0.1] * 1024 for _ in texts],
                "get_runtime_binding": lambda self: type(
                    "Binding",
                    (),
                    {"to_dict": lambda _self: {"resolved_mode": "online", "degraded_conditions": []}},
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_rerank_runtime_binding",
        lambda: type("Binding", (), {"to_dict": lambda self: {"resolved_mode": "online", "degraded_conditions": []}})(),
    )

    pack = retrieve_evidence(
        query="请总结这篇论文的核心贡献",
        user_id="u-1",
        paper_scope=["paper-1"],
        query_family="fact",
        stage="rule",
    )

    assert retriever.kwargs is not None
    assert retriever.kwargs["paper_scope"] == ["paper-1"]
    assert len(pack.candidates) == 1
    assert pack.candidates[0].paper_id == "paper-1"


def test_main_path_retrieve_evidence_honors_empty_paper_scope(monkeypatch) -> None:
    retriever = _CapturingRetriever()
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._get_retriever",
        lambda stage, embedding_model: retriever,
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.create_embedding_provider",
        lambda provider, model: type(
            "Provider",
            (),
            {
                "dim": 1024,
                "embed_texts": lambda self, texts: [[0.1] * 1024 for _ in texts],
                "get_runtime_binding": lambda self: type(
                    "Binding",
                    (),
                    {"to_dict": lambda _self: {"resolved_mode": "online", "degraded_conditions": []}},
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_rerank_runtime_binding",
        lambda: type("Binding", (), {"to_dict": lambda self: {"resolved_mode": "online", "degraded_conditions": []}})(),
    )

    pack = retrieve_evidence(
        query="空知识库范围",
        user_id="u-1",
        paper_scope=[],
        query_family="fact",
        stage="rule",
    )

    assert retriever.kwargs is not None
    assert retriever.kwargs["paper_scope"] == []
    assert pack.candidates == []
    assert pack.diagnostics["paper_scope_filter_applied"] == 1.0
    assert pack.diagnostics["paper_scope_filter_size"] == 0.0


@pytest.mark.asyncio
async def test_build_answer_contract_payload_resolves_kb_scope_into_retrieval_scope(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.rag_v3.main_path_service._resolve_kb_paper_scope",
        lambda **kwargs: __import__("asyncio").sleep(0, result=["paper-kb-1", "paper-kb-2"]),
    )

    class _RoutingService:
        def route(self, *, query, query_family, paper_scope):
            captured["routing_paper_scope"] = list(paper_scope or [])
            return SimpleNamespace(
                query_family=query_family or "fact",
                execution_mode="rag",
                task_family="read",
                truthfulness_required=True,
                retrieval_depth="standard",
                retrieval_model_policy="flash",
                retrieval_plane_policy={"mode": "rag"},
            )

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_phase_i_routing_service",
        lambda: _RoutingService(),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._resolve_runtime_execution_mode",
        lambda requested_execution_mode, paper_scope: ("rag", []),
    )

    def _fake_retrieve_evidence(**kwargs):
        captured["retrieval_paper_scope"] = list(kwargs.get("paper_scope") or [])
        return EvidencePack(
            query_id="q-kb",
            query=str(kwargs["query"]),
            query_family="fact",
            stage="rule",
            candidates=[
                EvidenceCandidate(
                    source_chunk_id="chunk-kb-1",
                    paper_id="paper-kb-1",
                    section_id="intro",
                    content_type="text",
                    anchor_text="kb scoped evidence",
                    rerank_score=0.92,
                )
            ],
            diagnostics={"runtime_truth": {"degraded_conditions": []}},
        )

    monkeypatch.setattr("app.rag_v3.main_path_service.retrieve_evidence", _fake_retrieve_evidence)
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.score_evidence",
        lambda pack: SimpleNamespace(citation_support_score=1.0, evidence_relevance_score=0.88),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_answer_contract",
        lambda pack, quality: SimpleNamespace(answer_mode="partial", missing_evidence=[], claims=[]),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._load_paper_display_title_map",
        lambda user_id, paper_ids: __import__("asyncio").sleep(
            0, result={paper_id: f"title-{paper_id}" for paper_id in paper_ids or []}
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_evidence_source_payload",
        lambda source_chunk_id: {
            "content": "kb scoped evidence body",
            "page_num": 1,
            "section_path": "intro",
        },
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_citation_jump_url",
        lambda paper_id, source_chunk_id: f"/read/{paper_id}/{source_chunk_id}",
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: __import__("asyncio").sleep(0, result="KB scoped answer"),
    )

    class _TruthfulnessService:
        def evaluate_text(self, *, text, evidence_blocks):
            return {
                "answerMode": "partial",
                "unsupportedClaimRate": 0.0,
                "summary": {"supportedClaimCount": 1},
                "results": [],
            }

        def report_to_answer_claims(self, report):
            return []

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_truthfulness_service",
        lambda: _TruthfulnessService(),
    )
    monkeypatch.setattr("app.rag_v3.main_path_service.build_recovery_actions", lambda **kwargs: [])

    payload = await build_answer_contract_payload(
        query="请基于知识库回答",
        user_id="user-1",
        kb_id="kb-1",
    )

    assert captured["routing_paper_scope"] == ["paper-kb-1", "paper-kb-2"]
    assert captured["retrieval_paper_scope"] == ["paper-kb-1", "paper-kb-2"]
    assert payload["diagnostics"]["kb_scope_resolution"]["resolved_paper_scope_size"] == 2


@pytest.mark.asyncio
async def test_build_answer_contract_payload_preserves_empty_kb_scope(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.rag_v3.main_path_service._resolve_kb_paper_scope",
        lambda **kwargs: __import__("asyncio").sleep(0, result=[]),
    )

    class _RoutingService:
        def route(self, *, query, query_family, paper_scope):
            captured["routing_paper_scope"] = paper_scope
            return SimpleNamespace(
                query_family=query_family or "fact",
                execution_mode="global_review",
                task_family="read",
                truthfulness_required=True,
                retrieval_depth="standard",
                retrieval_model_policy="flash",
                retrieval_plane_policy={"mode": "global_review"},
            )

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_phase_i_routing_service",
        lambda: _RoutingService(),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._resolve_runtime_execution_mode",
        lambda requested_execution_mode, paper_scope: ("local_evidence", ["global_review_fallback_to_local_evidence"])
        if paper_scope == []
        else ("local_evidence", []),
    )

    def _fake_retrieve_evidence(**kwargs):
        captured["retrieval_paper_scope"] = kwargs.get("paper_scope")
        return EvidencePack(
            query_id="q-kb-empty",
            query=str(kwargs["query"]),
            query_family="fact",
            stage="rule",
            candidates=[],
            diagnostics={"runtime_truth": {"degraded_conditions": []}},
        )

    monkeypatch.setattr("app.rag_v3.main_path_service.retrieve_evidence", _fake_retrieve_evidence)
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.score_evidence",
        lambda pack: SimpleNamespace(citation_support_score=0.0, evidence_relevance_score=0.0),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_answer_contract",
        lambda pack, quality: SimpleNamespace(answer_mode="abstain", missing_evidence=[], claims=[]),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._load_paper_display_title_map",
        lambda user_id, paper_ids: __import__("asyncio").sleep(0, result={}),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: __import__("asyncio").sleep(0, result="证据不足"),
    )

    class _TruthfulnessService:
        def evaluate_text(self, *, text, evidence_blocks):
            return {
                "answerMode": "abstain",
                "unsupportedClaimRate": 0.0,
                "summary": {"supportedClaimCount": 0},
                "results": [],
            }

        def report_to_answer_claims(self, report):
            return []

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_truthfulness_service",
        lambda: _TruthfulnessService(),
    )
    monkeypatch.setattr("app.rag_v3.main_path_service.build_recovery_actions", lambda **kwargs: [])

    payload = await build_answer_contract_payload(
        query="请基于空知识库回答",
        user_id="user-1",
        kb_id="kb-empty",
    )

    assert captured["routing_paper_scope"] == []
    assert captured["retrieval_paper_scope"] == []
    assert payload["diagnostics"]["kb_scope_resolution"]["resolved_paper_scope_size"] == 0
    assert payload["diagnostics"]["kb_scope_resolution"]["empty_scope_preserved"] is True
    assert "kb_scope_empty" in payload["degraded_conditions"]
