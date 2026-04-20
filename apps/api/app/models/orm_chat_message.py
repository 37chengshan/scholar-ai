"""SQLAlchemy ORM model for ChatMessage.

Contains:
- ChatMessage: Message in a chat session

Table name matches Prisma schema (chat_messages).

Phase 5.2 (2026-04-14): Added thinking-related fields for future persistence.
These fields are RESERVED but NOT IMPLEMENTED in this phase:
- reasoning_content: Agent reasoning/thinking content
- current_phase: Current processing phase
- tool_timeline: Tool call execution timeline
- citations: Source citations for responses
- stream_status: Streaming status indicator
- tokens_used: Token consumption
- cost: API cost in USD
- duration_ms: Response duration

NOTE: This phase does NOT implement persistence. Fields are nullable placeholders
for Phase 2 implementation (thinking history across sessions).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.orm_session import Session


class ChatMessage(Base):
    """Chat message model.

    Matches Prisma schema 'chat_messages' table.

    Phase 5.2: Added thinking-related nullable fields for future persistence.
    These fields are NOT used in current phase - only structural placeholders.
    """

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # =================================================================
    # Phase 5.2: Thinking-related fields (RESERVED, NOT IMPLEMENTED)
    # These are nullable placeholders for future thinking persistence.
    # Current phase: Only session-internal thinking display, no DB writes.
    # =================================================================

    # Agent reasoning/thinking content (structured thinking blocks)
    reasoning_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Phase 5.2 reserved: Agent reasoning content (not implemented)"
    )

    # Current processing phase (e.g., 'planning', 'searching', 'synthesizing')
    current_phase: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Phase 5.2 reserved: Current agent phase (not implemented)"
    )

    # Tool call execution timeline (JSON array of tool events)
    tool_timeline: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Phase 5.2 reserved: Tool execution timeline (not implemented)"
    )

    # Source citations for agent responses
    citations: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Phase 5.2 reserved: Response citations (not implemented)"
    )

    # Streaming status indicator
    stream_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="Phase 5.2 reserved: Stream status (not implemented)"
    )

    # Token consumption for this message
    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Phase 5.2 reserved: Token usage (not implemented)"
    )

    # API cost in USD
    cost: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Phase 5.2 reserved: API cost (not implemented)"
    )

    # Response duration in milliseconds
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Phase 5.2 reserved: Response duration (not implemented)"
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="chat_messages")

    __table_args__ = (
        Index("idx_chat_messages_created_at", "created_at"),
        Index("idx_chat_messages_session_id", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"