from __future__ import annotations

import asyncio

from app.rag_v3.main_path_service import build_answer_contract_payload
from app.rag_v3.schemas import EvidenceBlock


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
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="这是一个有证据支持的回答。"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="test", user_id="u-1", query_family="fact", stage="rule", trace_id="trace-1"
    ))

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
    assert payload["task_family"] == "single_paper_fact"
    assert payload["execution_mode"] == "local_evidence"
    assert payload["truthfulness_required"] is True
    assert "truthfulness_summary" in payload
    assert "truthfulness_report" in payload


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
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="top k answer"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="top k test",
        user_id="u-1",
        stage="rule",
        top_k=2,
    ))

    assert captured["top_k"] == 2
    assert len(payload["citations"]) == 2
    assert len(payload["evidence_blocks"]) == 2


def test_answer_contract_normalizes_chat_prefix_and_uses_normalized_query(monkeypatch) -> None:
    captured: dict[str, object] = {}
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])

    def fake_retrieve_evidence(**kwargs):
        captured["query"] = kwargs["query"]
        return schemas.EvidencePack(
            query_id="q-normalized",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id="sid-1",
                    paper_id="p-1",
                    section_id="introduction",
                    content_type="text",
                    anchor_text="This paper reduces attention cost for long videos.",
                    rerank_score=0.92,
                )
            ],
            diagnostics={},
        )

    monkeypatch.setattr("app.rag_v3.main_path_service.retrieve_evidence", fake_retrieve_evidence)
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="该论文主要解决长视频建模中的高计算成本问题。"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="继续分析：请概括这篇论文主要解决什么问题。",
        user_id="u-1",
        stage="rule",
    ))

    assert captured["query"] == "请概括这篇论文主要解决什么问题。"
    assert payload["trace"]["query_normalized"] is True
    assert payload["trace"]["normalized_query"] == "请概括这篇论文主要解决什么问题。"


def test_truthfulness_fallback_keeps_supported_unstructured_answer_as_partial(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.truthfulness_service.get_claim_extractor",
        lambda: type("EmptyExtractor", (), {"extract": staticmethod(lambda _text: [])})(),
    )
    report = __import__("app.services.truthfulness_service", fromlist=["get_truthfulness_service"]).get_truthfulness_service().evaluate_text(
        text="该论文主要解决长视频理解中的高计算成本问题，并提出更高效的时空注意力设计。",
        evidence_blocks=[
            EvidenceBlock(
                evidence_id="e-1",
                source_chunk_id="e-1",
                paper_id="p-1",
                text="The paper reduces the computational cost of joint spatiotemporal attention for long videos.",
            )
        ],
    )

    assert report["answerMode"] == "partial"
    assert report["unsupportedClaimCount"] == 0


def test_summary_query_uses_summary_index_when_local_artifact_missing(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: schemas.EvidencePack(
            query_id="q-summary",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-summary-1",
                    paper_id="paper-1",
                    section_id="paper_summary",
                    content_type="text",
                    anchor_text="The paper introduces a preference alignment recipe with strong performance using only 1,000 curated examples.",
                    candidate_sources=["summary_index"],
                    rerank_score=0.88,
                )
            ],
            diagnostics={},
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_indexes_from_artifacts",
        lambda **kwargs: (
            type("PaperIndex", (), {"get": lambda self, paper_id: None})(),
            None,
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="这篇论文提出了一个只用少量高质量样本就能完成对齐的方法，并证明小而精的数据也能得到强模型表现。"),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="请概括这篇论文的核心贡献",
        user_id="u-1",
        paper_scope=["paper-1"],
        stage="rule",
    ))

    assert payload["citations"]
    assert payload["citations"][0]["source_chunk_id"] == "chunk-summary-1"
    assert payload["answer_mode"] in {"partial", "full"}
