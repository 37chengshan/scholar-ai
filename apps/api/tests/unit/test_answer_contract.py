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


def test_abstain_payload_keeps_single_paper_source_jump_fallback(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack"])

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: schemas.EvidencePack(
            query_id="q-abstain-fallback",
            query=kwargs["query"],
            query_family="fact",
            stage=kwargs["stage"],
            candidates=[],
            diagnostics={},
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="当前证据不足以给出可靠回答。"),
    )

    payload = asyncio.run(
        build_answer_contract_payload(
            query="请用一句话概括这篇论文的核心内容，并给出引用。",
            user_id="u-1",
            paper_scope=["paper-1"],
            stage="rule",
        )
    )

    assert payload["answer_mode"] == "abstain"
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["paper_id"] == "paper-1"
    assert payload["citations"][0]["source_chunk_id"] == "paper-scope-fallback::paper-1"
    assert payload["citations"][0]["citation_jump_url"].startswith("/read/paper-1")
    assert len(payload["evidence_blocks"]) == 1
    assert payload["evidence_blocks"][0]["source_chunk_id"] == "paper-scope-fallback::paper-1"
    assert payload["evidence_blocks"][0]["support_status"] == "unsupported"


def test_compare_payload_filters_summary_and_low_signal_display_citations(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: schemas.EvidencePack(
            query_id="q-compare-filter",
            query=kwargs["query"],
            query_family="compare",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-summary",
                    paper_id="paper-1",
                    section_id="_paper",
                    content_type="text",
                    anchor_text="[Paper Summary: Test Paper - Page 1] Test Paper - Page 1",
                    candidate_sources=["summary_index"],
                    rerank_score=0.95,
                ),
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-low-signal",
                    paper_id="paper-2",
                    section_id="introduction",
                    content_type="text",
                    anchor_text="a chain of thought, similar to the let's think step-by-step prompt.",
                    rerank_score=0.82,
                ),
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-method",
                    paper_id="paper-2",
                    section_id="methods",
                    content_type="text",
                    anchor_text="The method reduces alignment cost with 1000 curated examples.",
                    rerank_score=0.8,
                ),
            ],
            diagnostics={},
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="compare answer"),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._load_paper_display_title_map",
        lambda *args, **kwargs: asyncio.sleep(0, result={"paper-1": "test_5_pages", "paper-2": "LIMA: Less Is More for Alignment (v6)"}),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_indexes_from_artifacts",
        lambda **kwargs: (
            type("PaperIndex", (), {"get": lambda self, paper_id: None})(),
            None,
        ),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="继续分析两篇论文的核心差异与共同点",
        user_id="u-1",
        paper_scope=["paper-1", "paper-2"],
        query_family="compare",
        stage="rule",
    ))

    assert [citation["source_chunk_id"] for citation in payload["citations"]] == ["chunk-method"]
    assert payload["citations"][0]["title"] == "LIMA: Less Is More for Alignment (v6)"


def test_compare_payload_prefers_handoff_evidence_for_display(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: schemas.EvidencePack(
            query_id="q-compare-handoff",
            query=kwargs["query"],
            query_family="compare",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-summary",
                    paper_id="paper-1",
                    section_id="_paper",
                    content_type="text",
                    anchor_text="[Paper Summary: Test Paper - Page 1] Test Paper - Page 1",
                    candidate_sources=["summary_index"],
                    rerank_score=0.95,
                ),
            ],
            diagnostics={},
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(0, result="compare answer"),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._load_paper_display_title_map",
        lambda *args, **kwargs: asyncio.sleep(0, result={"paper-1": "test_5_pages", "paper-2": "LIMA: Less Is More for Alignment (v6)"}),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.build_indexes_from_artifacts",
        lambda **kwargs: (
            type("PaperIndex", (), {"get": lambda self, paper_id: None})(),
            None,
        ),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="继续分析两篇论文的核心差异与共同点",
        user_id="u-1",
        paper_scope=["paper-1", "paper-2"],
        query_family="compare",
        stage="rule",
        handoff_evidence=[
            {
                "handoff_id": "paper-1::results::chunk-compare-1::paper one reports a cheaper alignment path.",
                "paper_id": "paper-1",
                "source_chunk_id": "chunk-compare-1",
                "page_num": 2,
                "dimension_id": "results",
                "section_path": "results",
                "content_type": "text",
                "text": "Paper one reports a cheaper alignment path.",
                "title": "test_5_pages",
            },
            {
                "handoff_id": "paper-2::method::chunk-compare-2::paper two keeps data smaller while preserving quality.",
                "paper_id": "paper-2",
                "source_chunk_id": "chunk-compare-2",
                "page_num": 4,
                "dimension_id": "method",
                "section_path": "method",
                "content_type": "text",
                "text": "Paper two keeps data smaller while preserving quality.",
                "title": "LIMA: Less Is More for Alignment (v6)",
            },
        ],
    ))

    assert [citation["source_chunk_id"] for citation in payload["citations"][:2]] == [
        "chunk-compare-1",
        "chunk-compare-2",
    ]
    assert payload["citations"][0]["source_id"] == "paper-1::results::chunk-compare-1::paper one reports a cheaper alignment path."
    assert payload["evidence_blocks"][0]["section_path"] == "results"
    assert payload["evidence_blocks"][0]["evidence_id"] == "paper-1::results::chunk-compare-1::paper one reports a cheaper alignment path."
    assert payload["evidence_blocks"][1]["section_path"] == "method"


def test_compare_generation_falls_back_to_evidence_synthesis_when_model_abstains() -> None:
    from app.rag_v3.main_path_service import _generate_answer_from_citations

    async def _run() -> str:
        return await _generate_answer_from_citations(
            query="比较两篇论文的差异与共同点",
            query_family="compare",
            citations=[
                {
                    "paper_id": "paper-1",
                    "source_chunk_id": "chunk-1",
                    "section_path": "results",
                    "text_preview": "Paper one reports lower alignment cost under the evaluated setup.",
                    "title": "Paper One",
                },
                {
                    "paper_id": "paper-2",
                    "source_chunk_id": "chunk-2",
                    "section_path": "method",
                    "text_preview": "Paper two focuses on a smaller curated dataset while preserving quality.",
                    "title": "Paper Two",
                },
            ],
            paper_summaries=None,
        )

    from app.rag_v3 import main_path_service as target

    original_client = target.ZhipuLLMClient

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def simple_completion(self, *args, **kwargs) -> str:
            return "Insufficient evidence to answer confidently."

    target.ZhipuLLMClient = DummyClient
    try:
        answer = asyncio.run(_run())
    finally:
        target.ZhipuLLMClient = original_client

    assert "核心差异" in answer
    assert "下一步研究问题" in answer
    assert "Paper One" in answer
    assert "Paper Two" in answer
    assert "Insufficient evidence to answer confidently." not in answer


def test_compare_answer_contract_downgrades_abstain_to_partial_when_fallback_answer_is_grounded(monkeypatch) -> None:
    schemas = __import__("app.rag_v3.schemas", fromlist=["EvidencePack", "EvidenceCandidate"])

    monkeypatch.setattr(
        "app.rag_v3.main_path_service.retrieve_evidence",
        lambda **kwargs: schemas.EvidencePack(
            query_id="q-compare-fallback",
            query=kwargs["query"],
            query_family="compare",
            stage=kwargs["stage"],
            candidates=[
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-1",
                    paper_id="paper-1",
                    section_id="results",
                    content_type="text",
                    anchor_text="Paper one reports lower alignment cost.",
                    rerank_score=0.92,
                ),
                schemas.EvidenceCandidate(
                    source_chunk_id="chunk-2",
                    paper_id="paper-2",
                    section_id="method",
                    content_type="text",
                    anchor_text="Paper two keeps the dataset smaller while preserving quality.",
                    rerank_score=0.9,
                ),
            ],
            diagnostics={},
        ),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._load_paper_display_title_map",
        lambda *args, **kwargs: asyncio.sleep(0, result={"paper-1": "Paper One", "paper-2": "Paper Two"}),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._generate_answer_from_citations",
        lambda **kwargs: asyncio.sleep(
            0,
            result=(
                "基于当前证据，可以先确认两篇论文在研究切入点或实现路径上存在差异。\n\n"
                "核心差异：\n"
                "- Paper One 在 results 上的证据显示：Paper one reports lower alignment cost.\n"
                "- Paper Two 在 method 上的证据显示：Paper two keeps the dataset smaller while preserving quality.\n\n"
                "共同点：当前证据下共同点有限，现有证据主要支持各自的方法或结果。\n\n"
                "下一步研究问题：\n"
                "- Paper One 还需要补充方法假设与失败案例。\n"
                "- Paper Two 还需要补充与结果直接对应的证据。"
            ),
        ),
    )

    payload = asyncio.run(build_answer_contract_payload(
        query="比较两篇论文的核心差异与共同点",
        user_id="u-1",
        paper_scope=["paper-1", "paper-2"],
        query_family="compare",
        stage="rule",
    ))

    assert payload["answer_mode"] == "partial"
    assert payload["error_state"] == "partial_answer"
