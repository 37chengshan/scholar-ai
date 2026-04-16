"""Deprecated import shim for note schemas.

Use app.schemas.note for new imports.
"""

from app.schemas.note import NoteBase, NoteCreate, NoteListResponse, NoteResponse, NoteUpdate

__all__ = [
    "NoteBase",
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    "NoteListResponse",
]