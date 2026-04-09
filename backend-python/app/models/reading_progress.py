"""SQLAlchemy ORM model for ReadingProgress.

Contains:
- ReadingProgress: Track user's reading progress on papers

Table name matches Prisma schema (reading_progress).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class ReadingProgress(Base):
    """Reading progress tracking model.

    Matches Prisma schema 'reading_progress' table.
    """

    __tablename__ = "reading_progress"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    current_page: Mapped[int] = mapped_column(Integer, default=1)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    paper: Mapped["Paper"] = relationship(back_populates="reading_progress")
    user: Mapped["User"] = relationship(back_populates="reading_progress")

    __table_args__ = (
        UniqueConstraint("paper_id", "user_id", name="unique_paper_user"),
        Index("idx_reading_progress_last_read", "last_read_at"),
        Index("idx_reading_progress_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ReadingProgress(paper_id={self.paper_id}, user_id={self.user_id}, page={self.current_page})>"