"""Pydantic models for Session management."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionBase(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="active", pattern=r"^(active|archived|deleted)$")
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, pattern=r"^(active|archived|deleted)$")
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(...)
    user_id: str = Field(...)
    title: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="active")
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    message_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    last_activity_at: datetime = Field(...)
    expires_at: Optional[datetime] = Field(default=None)


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
