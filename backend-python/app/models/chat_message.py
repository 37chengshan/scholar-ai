"""Pydantic models for ChatMessage management.

Defines request/response schemas for:
- Chat message creation with role and content
- Chat message responses with complete message state
- Message role enum for agent conversations
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Message role in agent conversation.

    Follows Agent-Native architecture message types:
    - user: User questions and inputs
    - assistant: Agent responses and reasoning
    - tool: Tool execution results
    - system: System messages (permission confirmations, errors)
    """

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ChatMessageBase(BaseModel):
    """Base fields for ChatMessage model."""

    role: MessageRole = Field(
        ...,
        description="Message role (user, assistant, tool, system)",
    )
    content: str = Field(
        ...,
        description="Message content",
        min_length=1,
    )


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""

    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool call data for assistant messages",
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="Tool call ID for tool response correlation",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Message metadata (intent, confidence, citations)",
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Paper reference sources",
    )


class ChatMessageResponse(BaseModel):
    """Complete chat message data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        ...,
        description="Message UUID",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )
    session_id: str = Field(
        ...,
        description="Session UUID",
    )
    role: MessageRole = Field(
        ...,
        description="Message role",
    )
    content: str = Field(
        ...,
        description="Message content",
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool call data",
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="Tool call ID for correlation",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Message metadata",
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Paper reference sources",
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description="Token consumption for this message",
        ge=0,
    )
    duration_ms: Optional[int] = Field(
        default=None,
        description="Response time in milliseconds",
        ge=0,
    )
    created_at: datetime = Field(
        ...,
        description="Message creation timestamp",
    )


class ChatMessageListResponse(BaseModel):
    """Paginated list of chat messages."""

    messages: List[ChatMessageResponse] = Field(
        default_factory=list,
        description="List of messages",
    )
    total: int = Field(
        default=0,
        description="Total number of messages",
        ge=0,
    )
    session_id: str = Field(
        ...,
        description="Session UUID",
    )