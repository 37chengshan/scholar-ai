"""SQLAlchemy ORM model for User Memory (long-term memory storage).

Per D-11, D-12: Vector-based retrieval of user preferences, patterns, and feedback.
Used by MemorySearch service for context enrichment.

Table: user_memories
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserMemory(Base):
    """User memory model for long-term memory storage.

    Stores user preferences, patterns, and feedback for context enrichment.
    Vector embeddings are stored in Milvus for similarity search.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table
        content: Memory text content
        memory_type: Type of memory (preference, pattern, feedback)
        extra_data: Additional metadata as JSONB (renamed from 'metadata' to avoid SQLAlchemy reserved name)
        created_at: Creation timestamp
    """

    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    memory_type: Mapped[str] = mapped_column(String, index=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)  # Map to 'metadata' column in DB
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship to User
    user: Mapped["User"] = relationship("User", backref="memories")

    def __repr__(self) -> str:
        return f"<UserMemory(id={self.id}, user_id={self.user_id}, type={self.memory_type})>"


__all__ = ["UserMemory"]