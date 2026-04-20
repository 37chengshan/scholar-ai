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

# Annotation
from app.models.annotation import Annotation

# API key
from app.models.api_key import ApiKey
from app.models.batch import PaperBatch
from app.models.chat import (
    ChatConfirmRequest,
    ChatStreamRequest,
    ConfirmationRequiredEventData,
    ErrorEventData,
    MessageEventData,
    SSEEvent,
    SSEEventType,
    ToolCallEventData,
    ToolResultEventData,
)

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

# Config
from app.models.config import Config

# ImportJob (Wave 1 per D-03)
from app.models.import_batch import ImportBatch
from app.models.import_job import ImportJob

# KnowledgeBase
from app.models.knowledge_base import KnowledgeBase

# KnowledgeBasePaper (association table: many-to-many between KB and Paper)
from app.models.knowledge_base_paper import KnowledgeBasePaper

# Knowledge graph
from app.models.knowledge_map import KnowledgeMap
from app.models.note import (
    NoteBase,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
)
from app.models.note import (
    NoteCreate as NoteCreateSchema,
)
from app.models.notes_task import NotesTask

# Audit (ORM model)
from app.models.orm_audit_log import AuditLog
from app.models.orm_chat_message import ChatMessage

# Note (ORM model with different name to avoid conflict)
from app.models.orm_note import Note

# Session and Chat (ORM models)
from app.models.orm_session import Session

# Paper domain
from app.models.paper import Paper, PaperChunk

# Project
from app.models.project import Project

# Query
from app.models.query import Query
from app.models.rag import Citation, RAGQueryRequest, RAGResponse

# Reading progress
from app.models.reading_progress import ReadingProgress

# Retrieval schema (unified field names)
from app.models.retrieval import CitationSource, RetrievedChunk, SearchConstraints
from app.models.session import (
    SessionBase,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

# Processing
from app.models.task import ProcessingTask

# Token usage
from app.models.token_usage_log import TokenUsageLog

# Upload tracking
from app.models.upload_history import UploadHistory
from app.models.upload_session import UploadSession

# =============================================================================
# SQLAlchemy ORM Models
# =============================================================================
# User domain
from app.models.user import Permission, RefreshToken, Role, User, UserRole

# User memory (long-term memory storage)
from app.models.user_memory import UserMemory

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
    "KnowledgeBasePaper",
    "ImportBatch",
    "ImportJob",
    "ReadingProgress",
    "Session",
    "ChatMessage",
    "UploadHistory",
    "UploadSession",
    "PaperBatch",
    "Config",
    "KnowledgeMap",
    "AuditLog",
    "TokenUsageLog",
    "UserMemory",
    "ApiKey",
    # Retrieval schema
    "RetrievedChunk",
    "CitationSource",
    "SearchConstraints",
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
