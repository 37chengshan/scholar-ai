from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.review_draft import ReviewDraft
from app.rag_v3.schemas import EvidenceCandidate
from app.schemas.review_draft import (
    DraftDoc,
    DraftParagraph,
    DraftSection,
    EvidenceRetrieverOutput,
    DraftFinalizerInput,
    OutlineDoc,
    OutlineSection,
)
from app.services.review_draft_service import ReviewDraftService
from app.services.phase_i_routing_service import get_phase_i_routing_service


def test_validator_drops_paragraph_without_citations():
    service = ReviewDraftService(db=MagicMock())

    doc = DraftDoc(
        sections=[
            DraftSection(
                heading="Section A",
                paragraphs=[
                    DraftParagraph(
                        paragraph_id="p1",
                        text="no citations paragraph",
                        citations=[],
                        evidence_blocks=[],
                        citation_coverage_status="insufficient",
                    )
                ],
            )
        ]
    )

    validated, report = service._validate_draft(doc)

    assert len(report) == 1
    assert report[0].coverage_status == "insufficient"
    assert validated.sections[0].omitted_reason == "insufficient_evidence"
    assert validated.sections[0].paragraphs == []


def test_validator_keeps_paragraph_with_citations_and_evidence():
    service = ReviewDraftService(db=MagicMock())

    doc = DraftDoc(
        sections=[
            DraftSection(
                heading="Section A",
                paragraphs=[
                    DraftParagraph(
                        paragraph_id="p1",
                        text="has citations paragraph",
                        citations=[{"paper_id": "paper-1"}],
                        evidence_blocks=[
                            {
                                "evidence_id": "e1",
                                "source_type": "paper",
                                "paper_id": "paper-1",
                                "source_chunk_id": "chunk-1",
                                "content_type": "text",
                                "text": "snippet",
                                "citation_jump_url": "/read/paper-1?page=1",
                            }
                        ],
                        citation_coverage_status="covered",
                    )
                ],
            )
        ]
    )

    validated, report = service._validate_draft(doc)

    assert len(report) == 1
    assert report[0].coverage_status == "covered"
    assert validated.sections[0].omitted_reason is None
    assert len(validated.sections[0].paragraphs) == 1
    assert validated.sections[0].paragraphs[0].truthfulness_summary == {}


def test_finalize_marks_partial_when_some_sections_omitted():
    service = ReviewDraftService(db=MagicMock())

    doc = DraftDoc(
        sections=[
            DraftSection(
                heading="Kept",
                paragraphs=[
                    DraftParagraph(
                        paragraph_id="p1",
                        text="kept",
                        citations=[{"paper_id": "p1"}],
                        evidence_blocks=[
                            {
                                "evidence_id": "e1",
                                "source_type": "paper",
                                "paper_id": "p1",
                                "source_chunk_id": "c1",
                                "content_type": "text",
                                "text": "snippet",
                                "citation_jump_url": "/read/p1?page=1",
                            }
                        ],
                        citation_coverage_status="covered",
                    )
                ],
            ),
            DraftSection(heading="Dropped", paragraphs=[], omitted_reason="insufficient_evidence"),
        ]
    )

    final_input = DraftFinalizerInput(draft_doc=doc, coverage_report=[], run_metadata={})
    _, quality, error_state = service._finalize(
        finalizer_input=final_input,
        graph_used=True,
        graph_error=None,
        routing=get_phase_i_routing_service().route(
            query="Write a literature review of retrieval augmented generation",
            query_family="survey",
            paper_scope=["p1"],
        ),
    )

    assert quality.citation_coverage == 1.0
    assert quality.graph_assist_used is True
    assert quality.storm_lite_used is True
    assert error_state == "partial_draft"


def test_finalize_sets_fallback_when_graph_unavailable():
    service = ReviewDraftService(db=MagicMock())

    doc = DraftDoc(sections=[DraftSection(heading="Dropped", paragraphs=[], omitted_reason="insufficient_evidence")])
    final_input = DraftFinalizerInput(draft_doc=doc, coverage_report=[], run_metadata={})
    _, quality, error_state = service._finalize(
        finalizer_input=final_input,
        graph_used=False,
        graph_error="graph_unavailable",
        routing=get_phase_i_routing_service().route(
            query="Write a literature review of retrieval augmented generation",
            query_family="survey",
            paper_scope=["p1"],
        ),
    )

    assert quality.fallback_used is True
    assert error_state in {"insufficient_evidence", "partial_draft"}


def test_candidate_to_evidence_block_prefers_source_payload_content(mocker):
    mocker.patch(
        'app.services.review_draft_service.get_evidence_source_payload',
        return_value={
            "content": "Resolved chunk content",
            "page_num": 4,
            "section_path": "results",
            "citation_jump_url": "/read/paper-1?page=4&source=evidence&source_id=chunk-1",
            "anchor_text": "",
        },
    )

    block = ReviewDraftService._candidate_to_evidence_block(
        EvidenceCandidate(
            source_chunk_id="chunk-1",
            paper_id="paper-1",
            section_id="results",
            content_type="text",
            anchor_text="",
            rrf_score=0.5,
            rerank_score=0.8,
        )
    )

    assert block.text == "Resolved chunk content"
    assert block.page_num == 4


def test_retrieve_section_evidence_degrades_when_retriever_raises():
    service = ReviewDraftService(db=MagicMock())
    service._retrieve_evidence = MagicMock(side_effect=RuntimeError("milvus unavailable"))
    steps: list[dict] = []
    tool_events: list[dict] = []

    outputs = service._retrieve_section_evidence(
        user_id="user-1",
        paper_ids=["paper-1"],
        outline_doc=OutlineDoc(
            research_question="q",
            themes=["attention"],
            sections=[
                OutlineSection(
                    title="Method Trends",
                    intent="Compare methods",
                    perspective="methods",
                    retrieval_mode="global_review",
                    supporting_paper_ids=["paper-1"],
                    seed_evidence=[],
                )
            ],
        ),
        routing=get_phase_i_routing_service().route(
            query="Write a literature review of retrieval augmented generation",
            query_family="survey",
            paper_scope=["paper-1"],
        ),
        steps=steps,
        tool_events=tool_events,
    )

    assert len(outputs) == 1
    assert outputs[0].section_title == "Method Trends"
    assert outputs[0].evidence_bundles == []
    assert steps[-1]["step_name"] == "evidence_retriever"
    assert tool_events[-1]["status"] == "error"
    assert tool_events[-1]["result"]["error"] == "milvus unavailable"


def test_retrieve_section_evidence_uses_live_fallback_when_artifact_retrieval_is_empty(mocker):
    service = ReviewDraftService(db=MagicMock())
    service._retrieve_evidence = MagicMock(
        return_value=MagicMock(candidates=[], diagnostics={"paper_coverage_count": 0.0})
    )
    fallback_block = {
        "evidence_id": "milvus-1",
        "source_type": "paper",
        "paper_id": "paper-1",
        "source_chunk_id": "milvus-1",
        "content_type": "text",
        "text": "Live Milvus fallback evidence",
        "quote_text": "Live Milvus fallback evidence",
        "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=milvus-1",
    }
    mocker.patch.object(
        service,
        "_retrieve_live_evidence_fallback",
        return_value=[fallback_block],
    )
    steps: list[dict] = []
    tool_events: list[dict] = []

    outputs = service._retrieve_section_evidence(
        user_id="user-1",
        paper_ids=["paper-1"],
        outline_doc=OutlineDoc(
            research_question="q",
            themes=["attention"],
            sections=[
                OutlineSection(
                    title="Method Trends",
                    intent="Compare methods",
                    perspective="methods",
                    retrieval_mode="global_review",
                    supporting_paper_ids=["paper-1"],
                    seed_evidence=[],
                )
            ],
        ),
        routing=get_phase_i_routing_service().route(
            query="Write a literature review of retrieval augmented generation",
            query_family="survey",
            paper_scope=["paper-1"],
        ),
        steps=steps,
        tool_events=tool_events,
    )

    assert len(outputs) == 1
    assert outputs[0].evidence_bundles[0].text == "Live Milvus fallback evidence"
    assert tool_events[-1]["status"] == "success"
    assert tool_events[-1]["result"]["live_fallback_used"] is True


def test_write_draft_builds_storm_lite_benchmark_hooks():
    service = ReviewDraftService(db=MagicMock())
    routing = get_phase_i_routing_service().route(
        query="Write a literature review of retrieval augmented generation",
        query_family="survey",
        paper_scope=["paper-1", "paper-2"],
    )

    draft = service._write_draft(
        outline_doc=OutlineDoc(
            research_question="retrieval augmented generation",
            themes=["retrieval", "generation"],
            sections=[
                OutlineSection(
                    title="Method Trends",
                    intent="Compare methods and assumptions",
                    perspective="methods",
                    retrieval_mode="global_review",
                    supporting_paper_ids=["paper-1", "paper-2"],
                    seed_evidence=[],
                )
            ],
        ),
        section_evidence=[
            EvidenceRetrieverOutput(
                section_title="Method Trends",
                evidence_bundles=[
                    {
                        "evidence_id": "e1",
                        "source_type": "paper",
                        "paper_id": "paper-1",
                        "source_chunk_id": "chunk-1",
                        "content_type": "text",
                        "text": "Paper 1 introduces retrieval-augmented training.",
                        "citation_jump_url": "/read/paper-1?page=1",
                    },
                    {
                        "evidence_id": "e2",
                        "source_type": "paper",
                        "paper_id": "paper-2",
                        "source_chunk_id": "chunk-2",
                        "content_type": "text",
                        "text": "Paper 2 focuses on evidence calibration.",
                        "citation_jump_url": "/read/paper-2?page=1",
                    },
                ],
            )
        ],
        routing=routing,
    )

    paragraph = draft.sections[0].paragraphs[0]
    assert paragraph.benchmark_hooks["execution_mode"] == "global_review"
    assert paragraph.benchmark_hooks["review_strategy"] == "storm_lite"
    assert paragraph.truthfulness_summary["verifier_backend"] == "rarr_cove_scifact_lite"


@pytest.mark.asyncio
async def test_repair_claim_reassigns_fresh_draft_payload(mocker):
    db = AsyncMock()
    service = ReviewDraftService(db=db)
    original_payload = {
        "sections": [
            {
                "paragraphs": [
                    {
                        "paragraph_id": "p1",
                        "claim_verification": [
                            {
                                "claim_id": "c1",
                                "claim_text": "Original claim",
                                "claim_type": "factual",
                                "support_status": "unsupported",
                            }
                        ],
                        "evidence_blocks": [
                            {
                                "source_chunk_id": "chunk-1",
                                "text": "Evidence text",
                            }
                        ],
                    }
                ]
            }
        ]
    }
    draft = ReviewDraft(
        id="draft-1",
        knowledge_base_id="kb-1",
        user_id="user-1",
        title="Draft",
        draft_doc=original_payload,
    )
    mocker.patch.object(service, "get_draft", AsyncMock(return_value=draft))
    mocker.patch(
        "app.services.review_draft_service.get_truthfulness_service",
        return_value=MagicMock(
            repair_claim=MagicMock(
                return_value={
                    "claim_id": "c1",
                    "text": "Original claim",
                    "claim_type": "factual",
                    "support_level": "supported",
                    "evidence_ids": ["chunk-1"],
                    "support_score": 0.91,
                    "repairable": False,
                    "repair_hint": "verified",
                }
            ),
            evaluate_text=MagicMock(
                return_value={
                    "summary": {"answer_mode": "full"},
                    "results": [
                        {
                            "claim_id": "c1",
                            "text": "Original claim",
                            "claim_type": "factual",
                            "support_level": "supported",
                            "support_score": 0.91,
                            "evidence_ids": ["chunk-1"],
                            "reason": "verified",
                        }
                    ],
                }
            ),
        ),
    )

    await service.repair_claim(
        kb_id="kb-1",
        draft_id="draft-1",
        paragraph_id="p1",
        claim_id="c1",
        user_id="user-1",
    )

    assert draft.draft_doc is not original_payload
    assert (
        draft.draft_doc["sections"][0]["paragraphs"][0]["claim_verification"][0]["support_status"]
        == "supported"
    )
    assert draft.draft_doc["sections"][0]["paragraphs"][0]["truthfulness_summary"]["answer_mode"] == "full"
    db.flush.assert_awaited()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_repair_claim_rebuilds_all_claim_rows_from_refreshed_report(mocker):
    db = AsyncMock()
    service = ReviewDraftService(db=db)
    draft = ReviewDraft(
        id="draft-1",
        knowledge_base_id="kb-1",
        user_id="user-1",
        title="Draft",
        draft_doc={
            "sections": [
                {
                    "paragraphs": [
                        {
                            "paragraph_id": "p1",
                            "text": "Claim one. Claim two.",
                            "claim_verification": [
                                {"claim_id": "c1", "claim_text": "Claim one", "claim_type": "factual", "support_status": "unsupported"},
                                {"claim_id": "c2", "claim_text": "Claim two", "claim_type": "factual", "support_status": "unsupported"},
                            ],
                            "evidence_blocks": [{"source_chunk_id": "chunk-1", "text": "Evidence text"}],
                        }
                    ]
                }
            ]
        },
    )
    mocker.patch.object(service, "get_draft", AsyncMock(return_value=draft))
    mocker.patch(
        "app.services.review_draft_service.get_truthfulness_service",
        return_value=MagicMock(
            repair_claim=MagicMock(
                return_value={
                    "claim_id": "c1",
                    "text": "Claim one",
                    "claim_type": "factual",
                    "support_level": "supported",
                    "evidence_ids": ["chunk-1"],
                    "support_score": 0.8,
                    "repairable": False,
                    "repair_hint": "verified",
                }
            ),
            evaluate_text=MagicMock(
                return_value={
                    "summary": {"answer_mode": "partial"},
                    "results": [
                        {
                            "claim_id": "c1",
                            "text": "Claim one",
                            "claim_type": "factual",
                            "support_level": "supported",
                            "support_score": 0.8,
                            "evidence_ids": ["chunk-1"],
                            "reason": "verified",
                        },
                        {
                            "claim_id": "c2",
                            "text": "Claim two",
                            "claim_type": "factual",
                            "support_level": "partially_supported",
                            "support_score": 0.4,
                            "evidence_ids": ["chunk-1"],
                            "reason": "partial",
                        },
                    ],
                }
            ),
        ),
    )

    await service.repair_claim(
        kb_id="kb-1",
        draft_id="draft-1",
        paragraph_id="p1",
        claim_id="c1",
        user_id="user-1",
    )

    claim_rows = draft.draft_doc["sections"][0]["paragraphs"][0]["claim_verification"]
    assert len(claim_rows) == 2
    assert claim_rows[1]["claim_id"] == "c2"
    assert claim_rows[1]["support_status"] == "partially_supported"


@pytest.mark.asyncio
async def test_repair_claim_preserves_targeted_repair_result_when_refresh_disagrees(mocker):
    db = AsyncMock()
    service = ReviewDraftService(db=db)
    draft = ReviewDraft(
        id="draft-1",
        knowledge_base_id="kb-1",
        user_id="user-1",
        title="Draft",
        draft_doc={
            "sections": [
                {
                    "paragraphs": [
                        {
                            "paragraph_id": "p1",
                            "text": "Claim one. Claim two.",
                            "claim_verification": [
                                {"claim_id": "c1", "claim_text": "Claim one", "claim_type": "factual", "support_status": "unsupported"},
                                {"claim_id": "c2", "claim_text": "Claim two", "claim_type": "factual", "support_status": "unsupported"},
                            ],
                            "evidence_blocks": [{"source_chunk_id": "chunk-1", "text": "Evidence text"}],
                        }
                    ]
                }
            ]
        },
    )
    mocker.patch.object(service, "get_draft", AsyncMock(return_value=draft))
    mocker.patch(
        "app.services.review_draft_service.get_truthfulness_service",
        return_value=MagicMock(
            repair_claim=MagicMock(
                return_value={
                    "claim_id": "c1",
                    "text": "Claim one",
                    "claim_type": "factual",
                    "support_level": "supported",
                    "evidence_ids": ["chunk-1"],
                    "support_score": 0.92,
                    "repairable": False,
                    "repair_hint": "verified",
                }
            ),
            evaluate_text=MagicMock(
                return_value={
                    "summary": {"answer_mode": "abstain", "verifier_backend": "rarr_cove_scifact_lite"},
                    "results": [
                        {
                            "claim_id": "c1",
                            "text": "Claim one",
                            "claim_type": "factual",
                            "support_level": "unsupported",
                            "support_score": 0.1,
                            "evidence_ids": [],
                            "reason": "stale",
                        },
                        {
                            "claim_id": "c2",
                            "text": "Claim two",
                            "claim_type": "factual",
                            "support_level": "partially_supported",
                            "support_score": 0.4,
                            "evidence_ids": ["chunk-1"],
                            "reason": "partial",
                        },
                    ],
                }
            ),
        ),
    )

    await service.repair_claim(
        kb_id="kb-1",
        draft_id="draft-1",
        paragraph_id="p1",
        claim_id="c1",
        user_id="user-1",
    )

    claim_rows = draft.draft_doc["sections"][0]["paragraphs"][0]["claim_verification"]
    assert claim_rows[0]["claim_id"] == "c1"
    assert claim_rows[0]["support_status"] == "supported"
    assert claim_rows[0]["repairable"] is False
    assert claim_rows[0]["repair_hint"] == "verified"
    assert draft.draft_doc["sections"][0]["paragraphs"][0]["truthfulness_summary"]["supported_claims"] == 1
