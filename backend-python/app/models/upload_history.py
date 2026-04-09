"""SQLAlchemy ORM model for UploadHistory.

Contains:
- UploadHistory: Track file upload history

Table name matches Prisma schema (upload_history).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class UploadHistory(Base):
    """Upload history tracking model.

    Matches Prisma schema 'upload_history' table.
    """

    __tablename__ = "upload_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    paper_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("papers.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="PROCESSING")
    chunks_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="upload_history")
    paper: Mapped[Optional["Paper"]] = relationship("Paper", back_populates="upload_history")

    __table_args__ = (
        Index("idx_upload_history_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<UploadHistory(id={self.id}, filename={self.filename}, status={self.status})>"