"""SQLAlchemy ORM model for Processing Task.

Contains:
- ProcessingTask: Async PDF processing task tracking

Table name matches Prisma schema (processing_tasks).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import Paper


class ProcessingTask(Base):
    """Processing task for PDF parsing.

    Matches Prisma schema 'processing_tasks' table.
    """

    __tablename__ = "processing_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paper_id: Mapped[str] = mapped_column(
        ForeignKey("papers.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String, default="pending")
    storage_key: Mapped[str] = mapped_column(String)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="processing_task")

    __table_args__ = (
        Index("idx_processing_tasks_paper_id", "paper_id"),
        Index("idx_processing_tasks_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingTask(id={self.id}, paper_id={self.paper_id}, status={self.status})>"