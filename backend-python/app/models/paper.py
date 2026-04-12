"""SQLAlchemy ORM models for Paper domain.

Contains:
- Paper: Paper metadata and content
- PaperChunk: Text chunks for RAG retrieval

Table names match Prisma schema (papers, paper_chunks).
Column names use Prisma camelCase convention via 'name' parameter.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import ProcessingTask
    from app.models.annotation import Annotation
    from app.models.reading_progress import ReadingProgress
    from app.models.upload_history import UploadHistory
    from app.models.query import Query
    from app.models.batch import PaperBatch
    from app.models.project import Project
    from app.models.knowledge_base import KnowledgeBase


class Paper(Base):
    """Paper model with metadata and content.

    Matches Prisma schema 'papers' table with camelCase column names.
    """

    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String)
    authors: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, name="arxivId")
    pdf_url: Mapped[Optional[str]] = mapped_column(String, nullable=True, name="pdfUrl")
    pdf_path: Mapped[Optional[str]] = mapped_column(String, nullable=True, name="pdfPath")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imrad_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, name="imradJson")
    status: Mapped[str] = mapped_column(String, default="pending")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, name="fileSize")
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, name="pageCount")
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    citations: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), name="createdAt"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now(), name="updatedAt"
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), name="userId")
    storage_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reading_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes_version: Mapped[int] = mapped_column(Integer, default=0)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    project_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("projects.id"), nullable=True, name="projectId"
    )
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=True
    )
    batch_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("paper_batches.id"), nullable=True
    )
    upload_progress: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    upload_status: Mapped[Optional[str]] = mapped_column(String, default="pending")
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="papers")
    paper_chunks: Mapped[List["PaperChunk"]] = relationship(
        "PaperChunk",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    processing_task: Mapped[Optional["ProcessingTask"]] = relationship(
        "ProcessingTask", back_populates="paper", uselist=False
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="paper", cascade="all, delete-orphan"
    )
    reading_progress: Mapped[List["ReadingProgress"]] = relationship(
        "ReadingProgress", back_populates="paper", cascade="all, delete-orphan"
    )
    upload_history: Mapped[List["UploadHistory"]] = relationship(
        "UploadHistory", back_populates="paper"
    )
    batch: Mapped[Optional["PaperBatch"]] = relationship(
        "PaperBatch", back_populates="papers"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="papers"
    )
    knowledge_base: Mapped[Optional["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="papers"
    )

    __table_args__ = (
        UniqueConstraint("userId", "title", name="unique_user_title"),
        Index("idx_papers_userId", "userId"),
        Index("idx_papers_starred", "starred"),
        Index("idx_papers_batch_id", "batch_id"),
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title={self.title[:50]}...)>"


class PaperChunk(Base):
    """Paper text chunk for RAG retrieval.

    Matches Prisma schema 'paper_chunks' table.
    """

    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    content: Mapped[str] = mapped_column(Text)
    section: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, name="pageStart")
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, name="pageEnd")
    is_table: Mapped[bool] = mapped_column(Boolean, default=False, name="isTable")
    is_figure: Mapped[bool] = mapped_column(Boolean, default=False, name="isFigure")
    is_formula: Mapped[bool] = mapped_column(Boolean, default=False, name="isFormula")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), name="createdAt"
    )
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), name="paperId")

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="paper_chunks")

    __table_args__ = (Index("idx_paper_chunks_paper_id", "paperId"),)

    def __repr__(self) -> str:
        return f"<PaperChunk(id={self.id}, paper_id={self.paper_id})>"