from __future__ import annotations

from pathlib import Path


def test_notes_evidence_save() -> None:
    file_path = Path(__file__).resolve().parents[2] / "app" / "api" / "notes.py"
    content = file_path.read_text(encoding="utf-8")

    assert "class EvidenceNoteCreate" in content
    assert "class EvidenceBlockPayload" in content
    assert "@router.post(\"/evidence\"" in content
    assert "def save_evidence_note" in content
    assert "linked_evidence" in content
    assert "target_note_id" in content
