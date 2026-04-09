"""SQLAlchemy ORM model for KnowledgeMap.

Contains:
- KnowledgeMap: Knowledge graph metadata

Table name matches Prisma schema (knowledge_maps).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class KnowledgeMap(Base):
    """Knowledge graph metadata model.

    Matches Prisma schema 'knowledge_maps' table.
    """

    __tablename__ = "knowledge_maps"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="knowledge_maps")

    def __repr__(self) -> str:
        return f"<KnowledgeMap(id={self.id}, name={self.name})>"