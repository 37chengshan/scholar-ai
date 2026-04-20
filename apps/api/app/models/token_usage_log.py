"""SQLAlchemy ORM model for TokenUsageLog.

Contains:
- TokenUsageLog: Token consumption tracking

Table name matches Prisma schema (token_usage_logs).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.orm_session import Session


class TokenUsageLog(Base):
    """Token usage log for cost tracking.

    Matches Prisma schema 'token_usage_logs' table.
    """

    __tablename__ = "token_usage_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sessions.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(50))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer)
    cost_cny: Mapped[Decimal] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="token_usage_logs")
    session: Mapped[Optional["Session"]] = relationship("Session", back_populates="token_usage_logs")

    __table_args__ = (
        Index("idx_token_usage_session", "session_id"),
        Index("idx_token_usage_user_date", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TokenUsageLog(id={self.id}, model={self.model}, total_tokens={self.total_tokens})>"