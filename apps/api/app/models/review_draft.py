"""ReviewDraft and ReviewRun ORM models for KB-level review generation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class ReviewDraft(Base):
    """KB-level formal review draft resource.

    A single resource stores both outline_doc and draft_doc.
    """

    __tablename__ = "review_drafts"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    title: Mapped[str] = mapped_column(String(200), default="Review Draft")
    status: Mapped[str] = mapped_column(String(32), default="idle")

    source_paper_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    question: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    outline_doc: Mapped[dict] = mapped_column(JSON, default=dict)
    draft_doc: Mapped[dict] = mapped_column(JSON, default=dict)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)

    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_review_drafts_kb_user", "knowledge_base_id", "user_id"),
        Index("idx_review_drafts_status", "status"),
    )


class ReviewRun(Base):
    """Persistent run trace for KB review generation."""

    __tablename__ = "review_runs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    review_draft_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("review_drafts.id"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(32), default="queued")
    scope: Mapped[str] = mapped_column(String(32), default="full_kb")

    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list[dict]] = mapped_column(JSON, default=list)
    tool_events: Mapped[list[dict]] = mapped_column(JSON, default=list)
    artifacts: Mapped[list[dict]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)
    recovery_actions: Mapped[list[dict]] = mapped_column(JSON, default=list)

    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_review_runs_kb_user", "knowledge_base_id", "user_id"),
        Index("idx_review_runs_draft", "review_draft_id"),
        Index("idx_review_runs_status", "status"),
    )
