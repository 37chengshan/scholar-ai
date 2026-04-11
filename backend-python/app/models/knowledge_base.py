"""SQLAlchemy ORM model for KnowledgeBase.

Knowledge Base is an upgraded Project concept with additional configuration fields
for parsing, embedding, and search settings.

Per D-08, D-09: KB global configuration fields are set at creation and inherited by papers.

Table name: knowledge_bases
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.paper import Paper


class KnowledgeBase(Base):
    """KnowledgeBase model with KB-specific configuration fields.

    KB is an upgraded Project concept with configuration for:
    - Embedding model selection
    - Parse engine selection
    - Chunk strategy selection
    - Feature toggles (graph, IMRaD, chart understanding, multimodal, comparison)

    Per D-08: Config fields are set at creation and inherited by all papers imported to KB.
    """

    __tablename__ = "knowledge_bases"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    # Core fields
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=""
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="其他"
    )

    # Stats (computed, updated by backend when papers are added/removed)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)

    # KB configuration fields (per D-08, D-09)
    # These are set at KB creation and inherited by papers imported to this KB
    embedding_model: Mapped[str] = mapped_column(String, default="bge-m3")
    parse_engine: Mapped[str] = mapped_column(String, default="docling")
    chunk_strategy: Mapped[str] = mapped_column(String, default="by-paragraph")
    enable_graph: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_imrad: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_chart_understanding: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_multimodal_search: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_comparison: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="knowledge_bases")
    papers: Mapped[List["Paper"]] = relationship(
        "Paper",
        back_populates="knowledge_base",
        foreign_keys="[Paper.knowledge_base_id]",
    )

    __table_args__ = (
        Index("idx_knowledge_bases_user_id", "user_id"),
        Index("idx_knowledge_bases_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"
