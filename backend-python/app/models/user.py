"""SQLAlchemy ORM models for User domain.

Contains:
- User: User account with email/password authentication
- Role: User role definitions (admin, user, etc.)
- UserRole: Many-to-many relationship between users and roles
- RefreshToken: JWT refresh token storage

Table names match Prisma schema (users, roles, user_roles, refresh_tokens).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import Paper
    from app.models.query import Query
    from app.models.orm_note import Note
    from app.models.project import Project
    from app.models.knowledge_base import KnowledgeBase
    from app.models.annotation import Annotation
    from app.models.orm_session import Session
    from app.models.upload_history import UploadHistory
    from app.models.batch import PaperBatch
    from app.models.knowledge_map import KnowledgeMap
    from app.models.orm_audit_log import AuditLog
    from app.models.token_usage_log import TokenUsageLog
    from app.models.reading_progress import ReadingProgress
    from app.models.api_key import ApiKey


class User(Base):
    """User account model.

    Matches Prisma schema 'users' table.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Match Prisma camelCase column names
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=False), server_default=func.now()
    )

    # Relationships - defined with lazy="dynamic" to avoid circular loading issues
    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="user", cascade="all, delete-orphan"
    )
    roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    queries: Mapped[List["Query"]] = relationship(
        "Query", back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="user", cascade="all, delete-orphan"
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    upload_history: Mapped[List["UploadHistory"]] = relationship(
        "UploadHistory", back_populates="user", cascade="all, delete-orphan"
    )
    paper_batches: Mapped[List["PaperBatch"]] = relationship(
        "PaperBatch", back_populates="user", cascade="all, delete-orphan"
    )
    knowledge_maps: Mapped[List["KnowledgeMap"]] = relationship(
        "KnowledgeMap", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    token_usage_logs: Mapped[List["TokenUsageLog"]] = relationship(
        "TokenUsageLog", back_populates="user", cascade="all, delete-orphan"
    )
    reading_progress: Mapped[List["ReadingProgress"]] = relationship(
        "ReadingProgress", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Role(Base):
    """Role definition model.

    Matches Prisma schema 'roles' table.
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class UserRole(Base):
    """User-Role association model.

    Matches Prisma schema 'user_roles' table.
    """

    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("users.id"))
    role_id: Mapped[str] = mapped_column("roleId", ForeignKey("roles.id"))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (UniqueConstraint("userId", "roleId", name="user_role_unique"),)

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class RefreshToken(Base):
    """Refresh token storage model.

    Matches Prisma schema 'refresh_tokens' table.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"


class Permission(Base):
    """Permission definition model.

    Matches Prisma schema 'permissions' table.
    """

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resource: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)

    __table_args__ = (UniqueConstraint("resource", "action", name="permission_unique"),)

    def __repr__(self) -> str:
        return f"<Permission(resource={self.resource}, action={self.action})>"
