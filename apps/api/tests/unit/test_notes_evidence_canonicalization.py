from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.notes import (
    EvidenceBlockPayload,
    EvidenceNoteCreate,
    save_evidence_note,
)
from app.models.orm_note import Note


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_save_evidence_note_persists_canonical_source_chunk_id(mocker):
    mocker.patch(
        "app.api.notes.get_evidence_source_payload",
        return_value=None,
    )
    mocker.patch(
        "app.api.notes._find_best_evidence_source_payload_db",
        new=AsyncMock(return_value=None),
    )
    mocker.patch(
        "app.api.notes.find_best_evidence_source_payload",
        return_value={
            "paper_id": "paper-1",
            "source_chunk_id": "chunk-fixed-1",
            "page_num": 3,
            "section_path": "introduction",
            "content_type": "text",
            "content": "canonical evidence",
            "citation_jump_url": "/read/paper-1?page=3&source=chat&source_id=chunk-fixed-1",
        },
    )

    saved_notes: list[Note] = []

    def _add(note: Note) -> None:
        note.id = "note-1"
        saved_notes.append(note)

    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult(None)),
        add=_add,
        flush=AsyncMock(),
        refresh=AsyncMock(),
    )

    request = EvidenceNoteCreate(
        claim="test claim",
        evidence_block=EvidenceBlockPayload(
            evidence_id="466045819771397202",
            source_type="paper",
            paper_id="paper-1",
            source_chunk_id="466045819771397202",
            page_num=None,
            section_path="introduction",
            content_type="text",
            text="legacy evidence text",
        ),
        surface="chat",
    )

    response = await save_evidence_note(request=request, user_id="user-1", db=db)

    payload = response.data
    assert payload["linkedEvidence"][0]["source_chunk_id"] == "chunk-fixed-1"
    assert payload["linkedEvidence"][0]["citation_jump_url"].endswith("source_id=chunk-fixed-1")
    assert payload["paperIds"] == ["paper-1"]
    assert isinstance(payload["id"], str)

    # Ensure the persisted ORM note also carried canonical data before formatting.
    persisted_note = saved_notes[0]
    assert isinstance(persisted_note, Note)
    assert persisted_note.linked_evidence[0]["source_chunk_id"] == "466045819771397202"


@pytest.mark.asyncio
async def test_save_evidence_note_keeps_existing_note_body_when_targeting_note(mocker):
    mocker.patch(
        "app.api.notes.get_evidence_source_payload",
        return_value={
            "paper_id": "paper-1",
            "source_chunk_id": "chunk-fixed-2",
            "page_num": 2,
            "section_path": "introduction",
            "content_type": "text",
            "content": "canonical evidence",
            "citation_jump_url": "/read/paper-1?page=2&source=read&source_id=chunk-fixed-2",
        },
    )
    mocker.patch(
        "app.api.notes._canonicalize_linked_evidence",
        new=AsyncMock(side_effect=lambda items, db=None: items),
    )

    note = Note(
        id="note-existing",
        user_id="user-1",
        title="Paper · 阅读笔记",
        source_type="read",
        tags=["read-note"],
        paper_ids=["paper-1"],
        linked_evidence=[],
        content="Existing body",
        content_doc={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Existing body"}],
                }
            ],
        },
    )

    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult(note)),
        add=lambda _note: None,
        flush=AsyncMock(),
        refresh=AsyncMock(),
    )

    request = EvidenceNoteCreate(
        claim="当前阅读证据",
        evidence_block=EvidenceBlockPayload(
            evidence_id="chunk-legacy",
            source_type="paper",
            paper_id="paper-1",
            source_chunk_id="chunk-legacy",
            page_num=2,
            section_path="introduction",
            content_type="text",
            text="legacy evidence text",
        ),
        surface="read",
        target_note_id="note-existing",
    )

    response = await save_evidence_note(request=request, user_id="user-1", db=db)

    payload = response.data
    assert payload["content"] == "Existing body"
    assert payload["linkedEvidence"][0]["source_chunk_id"] == "chunk-fixed-2"
    assert note.content == "Existing body"
    assert note.content_doc["content"][0]["content"][0]["text"] == "Existing body"
