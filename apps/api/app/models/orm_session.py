"""SQLAlchemy ORM model for Session.

Contains:
- Session: Chat session for agent conversations

Table name matches Prisma schema (sessions).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chat_message import ChatMessage
    from app.models.token_usage_log import TokenUsageLog


class Session(Base):
    """Chat session model for agent conversations.

    Matches Prisma schema 'sessions' table.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), default="active")
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )
    message_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
    token_usage_logs: Mapped[List["TokenUsageLog"]] = relationship(
        "TokenUsageLog", back_populates="session"
    )

    __table_args__ = (
        Index("idx_sessions_expires_at", "expires_at"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"