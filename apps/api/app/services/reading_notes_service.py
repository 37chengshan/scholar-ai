"""Shared reading notes persistence helpers.

Centralizes the ownership rule that `paper.reading_notes` stores the
system-generated summary, while user-editable notes remain in the `notes` table.
"""

from app.models.paper import Paper


def persist_generated_reading_notes(paper: Paper, notes: str) -> int:
    """Persist generated reading notes onto a Paper record.

    Returns the next notes version after the write.
    """
    next_version = (paper.notes_version or 0) + 1
    paper.reading_notes = notes
    paper.notes_version = next_version
    paper.is_notes_ready = bool(notes and notes.strip())
    paper.notes_failed = False
    return next_version


def build_generated_notes_payload(paper_id: str, notes: str, version: int) -> dict:
    """Build the canonical API payload for generated reading notes."""
    return {
        "paperId": paper_id,
        "notes": notes,
        "version": version,
    }