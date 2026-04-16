"""SQLAlchemy ORM model for KnowledgeBasePaper association.

Represents the many-to-many relationship between KnowledgeBase and Paper.
A paper can belong to multiple knowledge bases, and a knowledge base can
contain multiple papers.

Table name: knowledge_base_papers

This model was referenced in app/workers/import_worker.py but was missing,
causing Celery worker startup to crash with ImportError.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase
    from app.models.paper import Paper


class KnowledgeBasePaper(Base):
    """Association table linking papers to knowledge bases.

    Allows a paper to be associated with multiple knowledge bases without
    changing Paper.knowledge_base_id (which tracks the *primary* KB).
    This table is used by the import worker to explicitly attach an imported
    paper to the target knowledge base during the 'attaching_to_kb' stage.

    Columns:
        id:                  UUID primary key.
        knowledge_base_id:   FK → knowledge_bases.id (CASCADE DELETE).
        paper_id:            FK → papers.id (CASCADE DELETE).
        added_at:            Timestamp when the paper was attached to the KB.
    """

    __tablename__ = "knowledge_base_papers"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key → knowledge_bases
    knowledge_base_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Foreign key → papers
    paper_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamp
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships (lazy – avoid circular import at module load time)
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="knowledge_base_papers",
        lazy="select",
    )
    paper: Mapped["Paper"] = relationship(
        "Paper",
        back_populates="knowledge_base_papers",
        lazy="select",
    )

    # Constraints & indexes
    __table_args__ = (
        # A paper may only be linked to a given KB once.
        UniqueConstraint(
            "knowledge_base_id",
            "paper_id",
            name="uq_knowledge_base_papers_kb_paper",
        ),
        # Fast look-up of all papers in a KB.
        Index("idx_kbp_knowledge_base_id", "knowledge_base_id"),
        # Fast look-up of all KBs a paper belongs to.
        Index("idx_kbp_paper_id", "paper_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<KnowledgeBasePaper("
            f"kb={self.knowledge_base_id!r}, "
            f"paper={self.paper_id!r})>"
        )
