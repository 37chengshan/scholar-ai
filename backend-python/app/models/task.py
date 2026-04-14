"""SQLAlchemy ORM model for Processing Task.

Contains:
- ProcessingTask: Async PDF processing task tracking
- ParseTaskStage: Enum for parse task stages per D-12
- ParseTask: Child parse task with granular stage tracking

Table name matches Prisma schema (processing_tasks).
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.import_job import ImportJob


class ParseTaskStage(str, Enum):
    """Parse task stages per D-12.

    Stage progression:
    pending -> validating -> uploading -> parsing -> chunking
    -> extracting -> embedding -> indexing -> completed/partial_success/failed
    """
    PENDING = "pending"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EXTRACTING = "extracting"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


# Stage progress weights (cumulative) per D-12
STAGE_PROGRESS_WEIGHTS = {
    ParseTaskStage.PENDING: 0,
    ParseTaskStage.VALIDATING: 5,
    ParseTaskStage.UPLOADING: 10,
    ParseTaskStage.PARSING: 40,
    ParseTaskStage.CHUNKING: 55,
    ParseTaskStage.EXTRACTING: 65,
    ParseTaskStage.EMBEDDING: 80,
    ParseTaskStage.INDEXING: 90,
    ParseTaskStage.COMPLETED: 100,
    ParseTaskStage.PARTIAL_SUCCESS: 100,
    ParseTaskStage.FAILED: 0,
}


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

    # === 新增: checkpoint 路径引用（Per Review Fix #3: 不存大 JSON） ===
    checkpoint_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    checkpoint_storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checkpoint_version: Mapped[int] = mapped_column(Integer, default=0)

    # === 新增: 阶段耗时（JSON） ===
    stage_timings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # === 新增: 失败分类（统一 vocabulary） ===
    failure_stage: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === 新增: 重试标记（PostgreSQL Boolean，Per Review Fix #4） ===
    is_retryable: Mapped[bool] = mapped_column(Boolean, default=True)

    # === 新增: trace_id（Per Review Fix #8） ===
    trace_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="processing_task")
    import_jobs: Mapped[List["ImportJob"]] = relationship(
        "ImportJob", back_populates="processing_task"
    )

    __table_args__ = (
        Index("idx_processing_tasks_paper_id", "paper_id"),
        Index("idx_processing_tasks_status", "status"),
        Index("idx_processing_tasks_trace_id", "trace_id"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingTask(id={self.id}, paper_id={self.paper_id}, status={self.status})>"


class ParseTask(Base):
    """Child parse task for individual PDF processing.

    Per D-12: Granular per-file status tracking with stage progression.
    Tracks progress through parse pipeline stages with FK to parent BatchTask.
    """

    __tablename__ = "parse_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    batch_task_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("batch_tasks.id"), nullable=True
    )
    paper_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("papers.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[ParseTaskStage] = mapped_column(
        SQLEnum(ParseTaskStage), default=ParseTaskStage.PENDING
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_parse_tasks_batch_task_id", "batch_task_id"),
        Index("idx_parse_tasks_paper_id", "paper_id"),
        Index("idx_parse_tasks_stage", "stage"),
    )

    def calculate_progress(self) -> int:
        """Calculate progress from current stage per D-12."""
        return STAGE_PROGRESS_WEIGHTS.get(self.stage, 0)

    def advance_stage(self, next_stage: ParseTaskStage) -> None:
        """Advance to next stage and update progress.

        Args:
            next_stage: The target stage to advance to
        """
        self.stage = next_stage
        self.progress = self.calculate_progress()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error message.

        Args:
            error: Error description
        """
        self.stage = ParseTaskStage.FAILED
        self.error_message = error
        self.progress = 0

    def __repr__(self) -> str:
        return f"<ParseTask(id={self.id}, filename={self.filename}, stage={self.stage.value})>"