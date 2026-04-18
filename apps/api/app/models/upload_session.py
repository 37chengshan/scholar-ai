"""SQLAlchemy ORM model for resumable upload sessions."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.import_job import ImportJob


class UploadSession(Base):
    """Upload session state for chunked local-file import."""

    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: f"us_{uuid.uuid4().hex[:26]}"
    )
    import_job_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False)

    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_parts: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    uploaded_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )

    import_job: Mapped["ImportJob"] = relationship("ImportJob")

    __table_args__ = (
        Index("idx_upload_sessions_import_job", "import_job_id"),
        Index("idx_upload_sessions_user_status", "user_id", "status"),
        Index("idx_upload_sessions_hash_size", "file_sha256", "size_bytes"),
    )

    def __repr__(self) -> str:
        return f"<UploadSession(id={self.id}, import_job_id={self.import_job_id}, status={self.status})>"
