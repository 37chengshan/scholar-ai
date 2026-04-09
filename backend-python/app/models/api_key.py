"""SQLAlchemy ORM model for API keys.

Contains:
- ApiKey: User API key for external integrations

Table matches the api_keys table used in users.py.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ApiKey(Base):
    """API key model for user integrations.

    Stores hashed API keys for secure authentication.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    key_hash: Mapped[str] = mapped_column(String)
    prefix: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, user_id={self.user_id})>"