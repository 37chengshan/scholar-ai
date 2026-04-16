"""SQLAlchemy ORM model for Config.

Contains:
- Config: System configuration key-value store

Table name matches Prisma schema (configs).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Config(Base):
    """System configuration model.

    Matches Prisma schema 'configs' table.
    """

    __tablename__ = "configs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String, unique=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Config(key={self.key})>"