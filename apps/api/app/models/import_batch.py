"""SQLAlchemy ORM model for ImportBatch.

ImportBatch aggregates multiple ImportJobs in a batch import operation.
Per gpt意见.md Section 7.2: Aggregate status for multiple ImportJobs.

Contains:
- ImportBatch: Batch import aggregation with status counts

Table name: import_batches
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.knowledge_base import KnowledgeBase
    from app.models.import_job import ImportJob


class ImportBatch(Base):
    """Batch import aggregation table.

    Per gpt意见.md 7.2: Aggregate status for multiple ImportJobs in one batch.
    """

    __tablename__ = "import_batches"

    # Primary key - impb_ prefix for batch IDs
    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: f"impb_{uuid.uuid4().hex[:12]}",
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id"), nullable=False
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("knowledge_bases.id"), nullable=False
    )

    # Status aggregation
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created"
    )  # created/running/partial/completed/failed
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="import_batches")
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="import_batches"
    )
    import_jobs: Mapped[List["ImportJob"]] = relationship(
        "ImportJob", back_populates="batch"
    )

    # Indexes per gpt意见.md Section 7.2
    __table_args__ = (
        Index("idx_import_batches_user_kb", "user_id", "knowledge_base_id"),
        Index("idx_import_batches_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ImportBatch(id={self.id}, total_items={self.total_items}, status={self.status})>"


__all__ = ["ImportBatch"]