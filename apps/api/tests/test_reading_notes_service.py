from types import SimpleNamespace

from app.services.reading_notes_service import (
    build_generated_notes_payload,
    persist_generated_reading_notes,
)


def test_persist_generated_reading_notes_updates_paper_state():
    paper = SimpleNamespace(
        reading_notes=None,
        notes_version=2,
        is_notes_ready=False,
        notes_failed=True,
    )

    next_version = persist_generated_reading_notes(paper, 'summary content')

    assert next_version == 3
    assert paper.reading_notes == 'summary content'
    assert paper.notes_version == 3
    assert paper.is_notes_ready is True
    assert paper.notes_failed is False


def test_build_generated_notes_payload_returns_canonical_shape():
    payload = build_generated_notes_payload('paper-1', 'summary content', 4)

    assert payload == {
        'paperId': 'paper-1',
        'notes': 'summary content',
        'version': 4,
    }