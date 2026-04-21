from app.api.notes import SYSTEM_AI_NOTE_TAG, _is_system_ai_note, _sanitize_note_tags


def test_sanitize_note_tags_removes_system_ai_tag():
    tags = ['read-note', SYSTEM_AI_NOTE_TAG, 'folder:kb:1']

    assert _sanitize_note_tags(tags) == ['read-note', 'folder:kb:1']


def test_sanitize_note_tags_handles_none():
    assert _sanitize_note_tags(None) == []


def test_is_system_ai_note_detects_legacy_ai_tag():
    assert _is_system_ai_note(['read-note', SYSTEM_AI_NOTE_TAG]) is True
    assert _is_system_ai_note(['read-note']) is False
    assert _is_system_ai_note(None) is False