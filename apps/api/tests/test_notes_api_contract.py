from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.notes import (
    SYSTEM_AI_NOTE_TAG,
    GenerateNotesRequest,
    RegenerateNotesRequest,
    _is_system_ai_note,
    _sanitize_note_tags,
    export_notes,
    generate_notes,
    regenerate_notes,
)


def test_sanitize_note_tags_removes_system_ai_tag():
    tags = ['read-note', SYSTEM_AI_NOTE_TAG, 'folder:kb:1']

    assert _sanitize_note_tags(tags) == ['read-note', 'folder:kb:1']


def test_sanitize_note_tags_handles_none():
    assert _sanitize_note_tags(None) == []


def test_is_system_ai_note_detects_legacy_ai_tag():
    assert _is_system_ai_note(['read-note', SYSTEM_AI_NOTE_TAG]) is True
    assert _is_system_ai_note(['read-note']) is False
    assert _is_system_ai_note(None) is False


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_generate_notes_scopes_paper_lookup_by_user():
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(None)))

    with pytest.raises(HTTPException) as exc:
        await generate_notes(
            GenerateNotesRequest(paper_id="paper-1"),
            user_id="user-1",
            db=db,
        )

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    assert '"userId"' in str(statement.whereclause)


@pytest.mark.asyncio
async def test_regenerate_notes_scopes_paper_lookup_by_user():
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(None)))

    with pytest.raises(HTTPException) as exc:
        await regenerate_notes(
            RegenerateNotesRequest(
                paper_id="paper-1",
                modification_request="expand methods",
            ),
            user_id="user-1",
            db=db,
        )

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    assert '"userId"' in str(statement.whereclause)


@pytest.mark.asyncio
async def test_export_notes_scopes_paper_lookup_by_user():
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(None)))

    with pytest.raises(HTTPException) as exc:
        await export_notes(
            paper_id="paper-1",
            user_id="user-1",
            db=db,
        )

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    assert '"userId"' in str(statement.whereclause)
