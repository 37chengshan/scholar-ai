"""SQLAlchemy ORM model for Note.

Contains:
- Note: User notes with paper references

Table name matches Prisma schema (notes).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Note(Base):
    """User note with paper references.

    Matches Prisma schema 'notes' table.
    """

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    paper_ids: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notes")

    __table_args__ = (
        Index("idx_notes_user_id", "user_id"),
        Index("idx_notes_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Note(id={self.id}, title={self.title[:30]}...)>"