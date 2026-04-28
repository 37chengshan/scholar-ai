from __future__ import annotations

from app.api.notes import (
    _append_document_content,
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
