"""Chat DTO schemas for shared contract convergence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ChatMode = Literal["auto", "rag", "agent"]
ChatScopeType = Literal["paper", "knowledge_base", "general"]


class ChatScope(BaseModel):
    type: ChatScopeType
    paper_id: Optional[str] = None
    knowledge_base_id: Optional[str] = None


class SessionDto(BaseModel):
    id: str
    title: Optional[str] = None
    status: str = "active"
    message_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class MessageDto(BaseModel):
    id: str
    session_id: str
    role: Literal["user", "assistant", "tool", "system"]
    content: str
    tool_name: Optional[str] = None
    created_at: datetime
