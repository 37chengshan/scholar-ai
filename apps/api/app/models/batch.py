"""SQLAlchemy ORM model for PaperBatch.

Contains:
- PaperBatch: Batch upload tracking
- BatchTaskStatus: Enum for batch task overall status per D-12
- BatchTask: Parent batch task with child aggregation

Table name matches Prisma schema (paper_batches).
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class BatchTaskStatus(str, Enum):
    """Batch task overall status per D-12.

    Status progression:
    pending -> processing -> completed/partial/failed
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"  # All files succeeded
    PARTIAL = "partial"      # Some succeeded, some failed
    FAILED = "failed"        # All files failed


class PaperBatch(Base):
    """Paper batch upload model.

    Matches Prisma schema 'paper_batches' table.
    """

    __tablename__ = "paper_batches"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), name="userId")
    total_files: Mapped[int] = mapped_column(Integer)
    uploaded_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="uploading")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="paper_batches")
    papers: Mapped[List["Paper"]] = relationship("Paper", back_populates="batch")

    __table_args__ = (
        Index("idx_paper_batches_user_id", "userId"),
        Index("idx_paper_batches_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<PaperBatch(id={self.id}, total_files={self.total_files}, status={self.status})>"


class BatchTask(Base):
    """Parent batch task for multi-file upload tracking.

    Per D-12: Aggregates child ParseTask status with granular counts.
    Tracks overall progress with completed_files/failed_files aggregation.
    """

    __tablename__ = "batch_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    pending_files: Mapped[int] = mapped_column(Integer, default=0)
    overall_status: Mapped[BatchTaskStatus] = mapped_column(
        SQLEnum(BatchTaskStatus), default=BatchTaskStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_batch_tasks_user_id", "user_id"),
        Index("idx_batch_tasks_overall_status", "overall_status"),
    )

    def update_from_children(self, child_statuses: List[str]) -> None:
        """Update aggregate counts from child task statuses per D-12.

        Args:
            child_statuses: List of child task status strings
        """
        self.completed_files = sum(
            1 for s in child_statuses if s in ["completed", "partial_success"]
        )
        self.failed_files = sum(1 for s in child_statuses if s == "failed")
        self.pending_files = self.total_files - self.completed_files - self.failed_files

        # Update overall status based on counts
        if self.completed_files == self.total_files:
            self.overall_status = BatchTaskStatus.COMPLETED
        elif self.failed_files == self.total_files:
            self.overall_status = BatchTaskStatus.FAILED
        elif self.completed_files > 0:
            self.overall_status = BatchTaskStatus.PARTIAL
        else:
            self.overall_status = BatchTaskStatus.PROCESSING

    @property
    def progress_percent(self) -> int:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0
        return int((self.completed_files / self.total_files) * 100)

    def __repr__(self) -> str:
        return f"<BatchTask(id={self.id}, total_files={self.total_files}, completed={self.completed_files}, status={self.overall_status.value})>"