"""SQLAlchemy ORM model for Query.

Contains:
- Query: RAG query and response storage

Table name matches Prisma schema (queries).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class Query(Base):
    """RAG query and response model.

    Matches Prisma schema 'queries' table.
    """

    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    query_type: Mapped[str] = mapped_column(String, default="single")
    status: Mapped[str] = mapped_column(String, default="pending")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    paper_ids: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries")
    # Note: papers relationship removed - paper_ids is ARRAY(String) without FK constraint
    # Access papers via paper_ids list instead of ORM relationship

    __table_args__ = (
        Index("idx_queries_created_at", "created_at"),
        Index("idx_queries_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Query(id={self.id}, question={self.question[:50]}...)>"