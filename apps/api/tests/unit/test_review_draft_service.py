from __future__ import annotations

from unittest.mock import MagicMock

from app.rag_v3.schemas import EvidenceCandidate
from app.schemas.review_draft import DraftDoc, DraftParagraph, DraftSection, DraftFinalizerInput
from app.services.review_draft_service import ReviewDraftService


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
    )

    assert quality.citation_coverage == 1.0
    assert quality.graph_assist_used is True
    assert error_state == "partial_draft"


def test_finalize_sets_fallback_when_graph_unavailable():
    service = ReviewDraftService(db=MagicMock())

    doc = DraftDoc(sections=[DraftSection(heading="Dropped", paragraphs=[], omitted_reason="insufficient_evidence")])
    final_input = DraftFinalizerInput(draft_doc=doc, coverage_report=[], run_metadata={})
    _, quality, error_state = service._finalize(
        finalizer_input=final_input,
        graph_used=False,
        graph_error="graph_unavailable",
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
