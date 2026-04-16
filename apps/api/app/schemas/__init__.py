"""API schemas (Pydantic DTOs).

This package is the single source of truth for request/response models.
`app/models` should only contain ORM/persistence models.
"""

from app.schemas.common import ListMeta, ListResponse, SuccessResponse
from app.schemas.note import NoteBase, NoteCreate, NoteListResponse, NoteResponse, NoteUpdate
from app.schemas.papers import PaperListItem, PaperListQuery, PaperListResponse
from app.schemas.rag import Citation, RAGQueryRequest, RAGResponse
from app.schemas.session import (
    SessionBase,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

__all__ = [
    "SuccessResponse",
    "ListMeta",
    "ListResponse",
    "NoteBase",
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    "NoteListResponse",
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
    "Citation",
    "RAGQueryRequest",
    "RAGResponse",
    "PaperListQuery",
    "PaperListItem",
    "PaperListResponse",
]
