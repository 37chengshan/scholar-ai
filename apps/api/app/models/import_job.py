"""SQLAlchemy ORM model for ImportJob.

ImportJob is the central entity for the unified import system.
Per D-01: ImportJob-first pattern - create ImportJob before Paper entity.
Per D-03: Wave 1 only includes import_jobs table (batch/event deferred).
Per D-08: State machine with status and stage tracking.

Contains:
- ImportJob: Unified import task tracking with next_action guidance

Table name: import_jobs
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper
    from app.models.knowledge_base import KnowledgeBase
    from app.models.task import ProcessingTask
    from app.models.import_batch import ImportBatch


class ImportJob(Base):
    """ImportJob model for unified import system.

    Per D-01: ImportJob-first pattern - create before Paper entity.
    Per D-03: Wave 1 only - batch_id nullable for Wave 3 linkage.
    Per D-08: State machine with status/stage/progress tracking.

    next_action JSONB field guides frontend on what to do next:
    - {"type": "upload_file", "uploadUrl": "/api/v1/import-jobs/{id}/file"}
    - {"type": "awaiting_dedupe_decision", "matchedPaperId": "..."}
    - {"type": "retry", "message": "..."}
    """

    __tablename__ = "import_jobs"

    # Primary key - imp_ prefix for import job IDs
    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: f"imp_{uuid.uuid4().hex[:24]}"
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("knowledge_bases.id"), nullable=False
    )
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("import_batches.id"), nullable=True
    )  # Wave 3 linkage to ImportBatch

    # Source identification
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # local_file/arxiv/pdf_url/doi/semantic_scholar
    source_ref_raw: Mapped[str] = mapped_column(Text, nullable=False)  # User's raw input
    source_ref_normalized: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Canonical reference

    # External source reference
    external_source: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # arxiv/s2/doi
    external_paper_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )  # External system's paper ID
    external_version: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # e.g., arXiv version

    # State machine (per D-08)
    # status: created/queued/running/awaiting_user_action/completed/failed/cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    # stage: awaiting_input/resolving_source/fetching_metadata/downloading_pdf/...
    stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default="awaiting_input"
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100

    # Deduplication
    dedupe_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unchecked"
    )  # unchecked/checking/match_found/resolved
    dedupe_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="prompt"
    )  # prompt/reuse_auto/import_auto
    dedupe_match_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # paper_id/doi/arxiv_same_version/pdf_sha256/...
    dedupe_match_paper_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    dedupe_decision: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # reuse_existing/import_as_new_version/force_new_paper/cancel

    # Import options
    import_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="single"
    )  # single/batch
    auto_attach_to_kb: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="latest_if_unspecified"
    )

    # File info
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Resolved metadata (for frontend preview)
    resolved_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_authors: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    resolved_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resolved_venue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    external_ids: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSONB, nullable=True
    )  # {doi, arxiv, s2, corpusId, ...}

    # Result linkage
    paper_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("papers.id"), nullable=True
    )
    processing_task_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("processing_tasks.id"), nullable=True
    )

    # Error handling
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_detail: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Retry/idempotency
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Frontend guidance - ADDED per plan fix
    next_action: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # Example values:
    # {"type": "upload_file", "uploadUrl": "/api/v1/import-jobs/{id}/file"}
    # {"type": "awaiting_dedupe_decision", "matchedPaperId": "..."}
    # {"type": "retry", "message": "..."}

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="import_jobs")
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="import_jobs"
    )
    paper: Mapped[Optional["Paper"]] = relationship("Paper", back_populates="import_jobs")
    processing_task: Mapped[Optional["ProcessingTask"]] = relationship(
        "ProcessingTask", back_populates="import_jobs"
    )
    batch: Mapped[Optional["ImportBatch"]] = relationship(
        "ImportBatch", back_populates="import_jobs"
    )

    # Indexes per gpt意见.md Section 6.3
    __table_args__ = (
        Index("idx_import_jobs_user_created_at", "user_id", "created_at"),
        Index("idx_import_jobs_kb_status", "knowledge_base_id", "status", "created_at"),
        Index(
            "idx_import_jobs_external_source_paper", "external_source", "external_paper_id"
        ),
        Index("idx_import_jobs_file_sha256", "file_sha256"),
        Index("idx_import_jobs_paper_id", "paper_id"),
        Index("idx_import_jobs_batch_id", "batch_id"),
    )

    def __repr__(self) -> str:
        return f"<ImportJob(id={self.id}, source_type={self.source_type}, status={self.status})>"

    def set_next_action_upload(self) -> None:
        """Set next_action for local file upload."""
        self.next_action = {
            "type": "upload_file",
            "uploadUrl": f"/api/v1/import-jobs/{self.id}/file",
        }

    def set_next_action_dedupe_decision(
        self, matched_paper_id: str, match_type: str
    ) -> None:
        """Set next_action for dedupe decision."""
        self.next_action = {
            "type": "awaiting_dedupe_decision",
            "matchedPaperId": matched_paper_id,
            "matchType": match_type,
        }

    def set_next_action_retry(self, message: str) -> None:
        """Set next_action for retry after error."""
        self.next_action = {"type": "retry", "message": message}

    def clear_next_action(self) -> None:
        """Clear next_action when worker takes over."""
        self.next_action = None
