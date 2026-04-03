"""Pydantic models for API request/response schemas.

Exports all models for easy importing:
- Session models: SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
- ChatMessage models: ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse, MessageRole
- Note models: NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
- RAG models: RAGQueryRequest, RAGQueryResponse, Citation
"""

from app.models.chat_message import (
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageResponse,
    MessageRole,
)
from app.models.chat import (
    ChatStreamRequest,
    ChatConfirmRequest,
    SSEEvent,
    SSEEventType,
    ThoughtEventData,
    ToolCallEventData,
    ToolResultEventData,
    ConfirmationRequiredEventData,
    MessageEventData,
    ErrorEventData,
)
from app.models.note import (
    NoteBase,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
)
from app.models.rag import Citation, RAGQueryRequest, RAGResponse
from app.models.session import (
    SessionBase,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

__all__ = [
    # Session models
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
    # ChatMessage models
    "ChatMessageBase",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageListResponse",
    "MessageRole",
    # Chat API models
    "ChatStreamRequest",
    "ChatConfirmRequest",
    "SSEEvent",
    "SSEEventType",
    "ThoughtEventData",
    "ToolCallEventData",
    "ToolResultEventData",
    "ConfirmationRequiredEventData",
    "MessageEventData",
    "ErrorEventData",
    # Note models
    "NoteBase",
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    "NoteListResponse",
    # RAG models
    "RAGQueryRequest",
    "RAGResponse",
    "Citation",
]