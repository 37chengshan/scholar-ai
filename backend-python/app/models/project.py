"""SQLAlchemy ORM model for Project.

Contains:
- Project: User project for organizing papers

Table name matches Prisma schema (projects).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class Project(Base):
    """Project model for organizing papers.

    Matches Prisma schema 'projects' table.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String, default="#3B82F6")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    papers: Mapped[List["Paper"]] = relationship("Paper", back_populates="project")

    __table_args__ = (
        Index("idx_projects_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"