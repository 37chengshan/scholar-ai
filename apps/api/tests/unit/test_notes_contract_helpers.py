from __future__ import annotations

import pytest

from app.api.notes import (
    _append_document_content,
    _canonicalize_linked_evidence_item,
    _format_note_response_async,
    _format_note_response,
    _text_to_editor_document,
)
from app.models.orm_note import Note


def test_format_note_response_wraps_legacy_content_into_content_doc() -> None:
    note = Note(
        id="note-1",
        user_id="user-1",
        title="Legacy",
        content="plain legacy content",
        tags=[],
        paper_ids=["paper-1"],
    )

    payload = _format_note_response(note)

    assert payload["content"] == "plain legacy content"
    assert payload["contentDoc"]["type"] == "doc"
    assert payload["linkedEvidence"] == []
    assert payload["sourceType"] == "manual"


def test_format_note_response_keeps_structured_content_doc_and_linked_evidence() -> None:
    note = Note(
        id="note-2",
        user_id="user-1",
        title="Structured",
        content="mirrored text",
        content_doc=_text_to_editor_document("mirrored text"),
        linked_evidence=[
            {
                "evidence_id": "ev-1",
                "source_type": "paper",
                "paper_id": "paper-1",
                "source_chunk_id": "chunk-1",
                "text": "supported finding",
                "content_type": "text",
                "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=chunk-1",
            }
        ],
        source_type="chat",
        tags=["evidence"],
        paper_ids=["paper-1"],
    )

    payload = _format_note_response(note)

    assert payload["contentDoc"]["type"] == "doc"
    assert payload["linkedEvidence"][0]["evidence_id"] == "ev-1"
    assert payload["sourceType"] == "chat"


def test_append_document_content_preserves_legacy_content() -> None:
    appended = _append_document_content(
        None,
        _text_to_editor_document("new evidence"),
        "legacy body",
    )

    texts = [
        node["text"]
        for paragraph in appended["content"]
        for node in paragraph.get("content", [])
        if isinstance(node, dict) and isinstance(node.get("text"), str)
    ]

    assert texts == ["legacy body", "new evidence"]


@pytest.mark.asyncio
async def test_canonicalize_linked_evidence_item_repairs_legacy_numeric_source_id(mocker) -> None:
    mocker.patch(
        "app.api.notes.find_best_evidence_source_payload",
        return_value={
            "evidence_id": "chunk_aebd619a8c07b368ac8c323c",
            "source_type": "paper",
            "paper_id": "paper-1",
            "source_chunk_id": "chunk_aebd619a8c07b368ac8c323c",
            "page_num": 1,
            "section_path": "introduction",
            "content_type": "text",
            "content": "canonical content",
            "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=chunk_aebd619a8c07b368ac8c323c",
        },
    )

    payload = await _canonicalize_linked_evidence_item(
        {
            "evidence_id": "466045819771397202",
            "source_type": "paper",
            "paper_id": "paper-1",
            "source_chunk_id": "466045819771397202",
            "page_num": None,
            "section_path": "introduction",
            "content_type": "text",
            "text": "legacy content",
            "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=466045819771397202",
        }
    )

    assert payload["source_chunk_id"] == "chunk_aebd619a8c07b368ac8c323c"
    assert payload["evidence_id"] == "466045819771397202"
    assert payload["citation_jump_url"].endswith("source_id=chunk_aebd619a8c07b368ac8c323c")


@pytest.mark.asyncio
async def test_canonicalize_linked_evidence_item_matches_snapshot_wrapped_text(mocker) -> None:
    captured = {}

    def _resolver(**kwargs):
        captured.update(kwargs)
        return {
            "evidence_id": "chunk_aebd619a8c07b368ac8c323c",
            "source_type": "paper",
            "paper_id": "paper-1",
            "source_chunk_id": "chunk_aebd619a8c07b368ac8c323c",
            "page_num": 1,
            "section_path": "introduction",
            "content_type": "text",
            "content": "LIMA: Less Is More for Alignment",
            "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=chunk_aebd619a8c07b368ac8c323c",
        }

    mocker.patch("app.api.notes.find_best_evidence_source_payload", side_effect=_resolver)

    await _canonicalize_linked_evidence_item(
        {
            "evidence_id": "466045819771397202",
            "source_type": "paper",
            "paper_id": "paper-1",
            "source_chunk_id": "466045819771397202",
            "page_num": None,
            "section_path": "introduction",
            "content_type": "text",
            "text": "Claim: c\nPaper: paper-1\nPage: N/A\nSection: introduction\n\n[Paper: LIMA: Less Is More for Alignment]\n[Section: introduction]\n[Page:1]\nLIMA: Less Is More for Alignment",
            "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=466045819771397202",
        }
    )

    assert captured["page_num"] is None
    assert captured["text"] == "Claim: c\nPaper: paper-1\nPage: N/A\nSection: introduction\n\n[Paper: LIMA: Less Is More for Alignment]\n[Section: introduction]\n[Page:1]\nLIMA: Less Is More for Alignment"


@pytest.mark.asyncio
async def test_format_note_response_async_uses_db_fallback_for_legacy_source_ids(mocker) -> None:
    note = Note(
        id="note-3",
        user_id="user-1",
        title="Legacy evidence",
        content="legacy",
        linked_evidence=[
            {
                "evidence_id": "466045819771397202",
                "source_type": "paper",
                "paper_id": "paper-1",
                "source_chunk_id": "466045819771397202",
                "page_num": None,
                "section_path": "introduction",
                "content_type": "text",
                "text": "[Paper: Title]\n[Section: introduction]\n[Page:1]\nbody",
                "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=466045819771397202",
            }
        ],
        tags=[],
        paper_ids=["paper-1"],
    )

    mocker.patch("app.api.notes.find_best_evidence_source_payload", return_value=None)
    mocker.patch(
        "app.api.notes._find_best_evidence_source_payload_db",
        return_value={
            "evidence_id": "chunk-fixed-1",
            "source_type": "paper",
            "paper_id": "paper-1",
            "source_chunk_id": "chunk-fixed-1",
            "page_num": 1,
            "section_path": "introduction",
            "content_type": "text",
            "content": "body",
            "citation_jump_url": "/read/paper-1?page=1&source=evidence&source_id=chunk-fixed-1",
        },
    )

    payload = await _format_note_response_async(note, db=mocker.Mock())

    assert payload["linkedEvidence"][0]["source_chunk_id"] == "chunk-fixed-1"
    assert payload["linkedEvidence"][0]["citation_jump_url"].endswith("source_id=chunk-fixed-1")
