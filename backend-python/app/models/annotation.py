"""SQLAlchemy ORM model for Annotation.

Contains:
- Annotation: PDF annotations (highlights, notes)

Table name matches Prisma schema (annotations).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class Annotation(Base):
    """PDF annotation model.

    Matches Prisma schema 'annotations' table.
    """

    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String)
    page_number: Mapped[int] = mapped_column(Integer)
    position: Mapped[Dict[str, Any]] = mapped_column(JSON)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String, default="#FFEB3B")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="annotations")
    user: Mapped["User"] = relationship("User", back_populates="annotations")

    __table_args__ = (
        Index("idx_annotations_paper_id", "paper_id"),
        Index("idx_annotations_paper_page", "paper_id", "page_number"),
        Index("idx_annotations_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, paper_id={self.paper_id}, type={self.type})>"