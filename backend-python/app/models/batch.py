"""SQLAlchemy ORM model for PaperBatch.

Contains:
- PaperBatch: Batch upload tracking

Table name matches Prisma schema (paper_batches).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class PaperBatch(Base):
    """Paper batch upload model.

    Matches Prisma schema 'paper_batches' table.
    """

    __tablename__ = "paper_batches"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
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
        Index("idx_paper_batches_user_id", "user_id"),
        Index("idx_paper_batches_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<PaperBatch(id={self.id}, total_files={self.total_files}, status={self.status})>"