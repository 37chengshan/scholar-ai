"""Notes 生成任务表。

Per Review Fix #9: 独立任务表 + claim 抢占锁机制。
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import Paper


class NotesTask(Base):
    """Notes 生成任务表（独立于 ProcessingTask）。

    Per Review Fix #9: 独立任务表 + FOR UPDATE SKIP LOCKED 抢占机制。
    """

    __tablename__ = "notes_generation_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), unique=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/claimed/completed/failed

    # 抢占锁字段（Per Review Fix #9）
    claimed_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # worker_id
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 失败信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="notes_tasks")

    __table_args__ = (
        Index("idx_notes_tasks_status", "status"),
        Index("idx_notes_tasks_paper_id", "paper_id"),
    )

    def __repr__(self) -> str:
        return f"<NotesTask(id={self.id}, paper_id={self.paper_id}, status={self.status})>"