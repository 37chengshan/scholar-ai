from types import SimpleNamespace

from app.services.reading_card_service import (
    build_reading_card_doc,
    ensure_reading_card_doc,
    persist_generated_reading_card,
)



def test_build_reading_card_doc_freezes_required_slots():
    card = build_reading_card_doc(
        paper_id="paper-1",
        records=[
            {
                "source_chunk_id": "chunk-intro",
                "paper_id": "paper-1",
                "page_num": 1,
                "section_path": "introduction",
                "content_type": "text",
                "text": "This paper studies retrieval grounding for scientific reading.",
            },
            {
                "source_chunk_id": "chunk-method",
                "paper_id": "paper-1",
                "page_num": 3,
                "section_path": "methods",
                "content_type": "text",
                "text": "We use a section-aware encoder with explicit metadata filters.",
            },
            {
                "source_chunk_id": "chunk-result",
                "paper_id": "paper-1",
                "page_num": 6,
                "section_path": "results",
                "content_type": "table",
                "text": "Accuracy improves by 4.8 points over the baseline.",
            },
            {
                "source_chunk_id": "chunk-conclusion",
                "paper_id": "paper-1",
                "page_num": 8,
                "section_path": "conclusion",
                "content_type": "text",
                "text": "Section-aware extraction improves grounded reading workflows.",
            },
        ],
    )

    assert set(card.keys()) == {
        "research_question",
        "method",
        "experiment",
        "result",
        "conclusion",
        "limitation",
        "key_evidence",
    }
    assert card["method"]["evidence_blocks"][0]["source_chunk_id"] == "chunk-method"
    assert card["result"]["evidence_blocks"][0]["content_type"] == "table"
    assert card["key_evidence"]



def test_build_reading_card_doc_prefers_section_aware_candidates():
    card = build_reading_card_doc(
        paper_id="paper-2",
        records=[
            {
                "source_chunk_id": "chunk-global",
                "paper_id": "paper-2",
                "page_num": 1,
                "section_path": "introduction",
                "content_type": "text",
                "text": "This introduction mentions every part of the paper in broad terms.",
            },
            {
                "source_chunk_id": "chunk-method-1",
                "paper_id": "paper-2",
                "page_num": 4,
                "section_path": "methods/model",
                "content_type": "text",
                "text": "The method slot should come from this section-aware evidence block.",
            },
        ],
    )

    assert card["method"]["content"].startswith("The method slot should come from this section-aware")
    assert card["method"]["evidence_blocks"][0]["source_chunk_id"] == "chunk-method-1"



def test_persist_generated_reading_card_updates_paper_state():
    paper = SimpleNamespace(reading_card_doc=None)
    card = {"research_question": {"title": "Research Question", "content": "RQ", "evidence_blocks": []}, "method": {"title": "Method", "content": None, "evidence_blocks": []}, "experiment": {"title": "Experiment", "content": None, "evidence_blocks": []}, "result": {"title": "Result", "content": None, "evidence_blocks": []}, "conclusion": {"title": "Conclusion", "content": None, "evidence_blocks": []}, "limitation": {"title": "Limitation", "content": None, "evidence_blocks": []}, "key_evidence": []}

    persist_generated_reading_card(paper, card)

    assert paper.reading_card_doc == card



def test_ensure_reading_card_doc_generates_for_legacy_paper():
    paper = SimpleNamespace(
        id="paper-legacy",
        reading_card_doc=None,
        paper_chunks=[],
    )

    card = ensure_reading_card_doc(
        paper,
        records=[
            {
                "source_chunk_id": "chunk-legacy-1",
                "paper_id": "paper-legacy",
                "page_num": 2,
                "section_path": "results",
                "content_type": "text",
                "text": "Legacy papers can still backfill a structured reading card.",
            }
        ],
    )

    assert card is not None
    assert paper.reading_card_doc is not None
    assert card["result"]["evidence_blocks"][0]["citation_jump_url"].startswith("/read/paper-legacy")
