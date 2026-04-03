"""Pydantic models for Session management.

Defines request/response schemas for:
- Session creation with optional title and metadata
- Session updates with partial field updates
- Session responses with complete session state
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionBase(BaseModel):
    """Base fields for Session model."""

    title: Optional[str] = Field(
        default=None,
        description="Session title (auto-generated or user-set)",
        max_length=255,
    )
    status: str = Field(
        default="active",
        description="Session status: active, archived, deleted",
        pattern=r"^(active|archived|deleted)$",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Session metadata: {paper_ids: [], tags: [], intent: '...'}",
    )


class SessionCreate(SessionBase):
    """Schema for creating a new session."""

    pass


class SessionUpdate(BaseModel):
    """Schema for updating an existing session (partial updates)."""

    title: Optional[str] = Field(
        default=None,
        description="Updated session title",
        max_length=255,
    )
    status: Optional[str] = Field(
        default=None,
        description="Updated session status",
        pattern=r"^(active|archived|deleted)$",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated session metadata",
    )


class SessionResponse(BaseModel):
    """Complete session data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        ...,
        description="Session UUID",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )
    user_id: str = Field(
        ...,
        description="Owner user UUID",
    )
    title: Optional[str] = Field(
        default=None,
        description="Session title",
        max_length=255,
    )
    status: str = Field(
        default="active",
        description="Session status",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Session metadata",
    )
    message_count: int = Field(
        default=0,
        description="Number of messages in session",
        ge=0,
    )
    tool_call_count: int = Field(
        default=0,
        description="Number of tool calls made",
        ge=0,
    )
    created_at: datetime = Field(
        ...,
        description="Session creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )
    last_activity_at: datetime = Field(
        ...,
        description="Last activity timestamp",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp (30 days)",
    )


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    sessions: List[SessionResponse] = Field(
        default_factory=list,
        description="List of sessions",
    )
    total: int = Field(
        default=0,
        description="Total number of sessions",
        ge=0,
    )
    limit: int = Field(
        default=20,
        description="Number of sessions per page",
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0,
    )