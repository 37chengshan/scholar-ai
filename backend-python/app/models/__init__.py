"""SQLAlchemy ORM models and Pydantic schemas for ScholarAI.

This module exports:
- Base: SQLAlchemy declarative base for Alembic migrations
- SQLAlchemy ORM models (User, Paper, etc.)
- Pydantic schemas for API request/response (preserved from existing)

Usage for Alembic:
    from app.models import Base
    target_metadata = Base.metadata

Usage for ORM queries:
    from app.models import User, Paper, ProcessingTask
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == "..."))

Usage for API schemas:
    from app.models import SessionCreate, NoteCreate, etc.
"""

from app.database import Base

# =============================================================================
# SQLAlchemy ORM Models
# =============================================================================

# User domain
from app.models.user import User, Role, UserRole, RefreshToken, Permission

# Paper domain
from app.models.paper import Paper, PaperChunk

# Processing
from app.models.task import ProcessingTask
from app.models.notes_task import NotesTask

# Query
from app.models.query import Query

# Note (ORM model with different name to avoid conflict)
from app.models.orm_note import Note

# Annotation
from app.models.annotation import Annotation

# Project
from app.models.project import Project

# KnowledgeBase
from app.models.knowledge_base import KnowledgeBase

# Reading progress
from app.models.reading_progress import ReadingProgress

# Session and Chat (ORM models)
from app.models.orm_session import Session
from app.models.orm_chat_message import ChatMessage

# Upload tracking
from app.models.upload_history import UploadHistory
from app.models.batch import PaperBatch

# Config
from app.models.config import Config

# Knowledge graph
from app.models.knowledge_map import KnowledgeMap

# Audit (ORM model)
from app.models.orm_audit_log import AuditLog

# Token usage
from app.models.token_usage_log import TokenUsageLog

# User memory (long-term memory storage)
from app.models.user_memory import UserMemory

# API key
from app.models.api_key import ApiKey


# =============================================================================
# Pydantic API Schemas (preserved from existing)
# =============================================================================

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
    NoteCreate as NoteCreateSchema,
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


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base for Alembic
    "Base",
    # SQLAlchemy ORM Models
    "User",
    "Role",
    "UserRole",
    "RefreshToken",
    "Permission",
    "Paper",
    "PaperChunk",
    "ProcessingTask",
    "NotesTask",
    "Query",
    "Note",
    "Annotation",
    "Project",
    "KnowledgeBase",
    "ReadingProgress",
    "Session",
    "ChatMessage",
    "UploadHistory",
    "PaperBatch",
    "Config",
    "KnowledgeMap",
    "AuditLog",
    "TokenUsageLog",
    "UserMemory",
    "ApiKey",
    # Pydantic API Schemas
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
    "ChatMessageBase",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageListResponse",
    "MessageRole",
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
    "NoteBase",
    "NoteCreateSchema",
    "NoteUpdate",
    "NoteResponse",
    "NoteListResponse",
    "RAGQueryRequest",
    "RAGResponse",
    "Citation",
]
