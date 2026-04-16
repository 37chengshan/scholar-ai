"""Pydantic models for ChatMessage management.

Defines request/response schemas for:
- Chat message creation with role and content
- Chat message responses with complete message state
- Message role enum for agent conversations

Phase 5.2 (2026-04-14): Added thinking-related fields for future persistence.
These fields are RESERVED but NOT IMPLEMENTED in this phase:
- reasoning_content: Agent reasoning/thinking content
- current_phase: Current processing phase
- tool_timeline: Tool call execution timeline
- citations: Source citations for responses
- stream_status: Streaming status indicator
- cost: API cost in USD

NOTE: This phase does NOT implement persistence. Fields are nullable placeholders
for Phase 2 implementation (thinking history across sessions).
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
    """Complete chat message data for API responses.

    Phase 5.2: Added thinking-related nullable fields for future persistence.
    These fields are NOT used in current phase - only structural placeholders.
    """

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

    # =================================================================
    # Phase 5.2: Thinking-related fields (RESERVED, NOT IMPLEMENTED)
    # These are nullable placeholders for future thinking persistence.
    # Current phase: Only session-internal thinking display, no DB writes.
    # =================================================================

    # Agent reasoning/thinking content
    reasoning_content: Optional[str] = Field(
        default=None,
        description="Phase 5.2 reserved: Agent reasoning content (not implemented)",
    )

    # Current processing phase (e.g., 'planning', 'searching', 'synthesizing')
    current_phase: Optional[str] = Field(
        default=None,
        description="Phase 5.2 reserved: Current agent phase (not implemented)",
        max_length=50,
    )

    # Tool call execution timeline (JSON array of tool events)
    tool_timeline: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Phase 5.2 reserved: Tool execution timeline (not implemented)",
    )

    # Source citations for agent responses
    citations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Phase 5.2 reserved: Response citations (not implemented)",
    )

    # Streaming status indicator
    stream_status: Optional[str] = Field(
        default=None,
        description="Phase 5.2 reserved: Stream status (not implemented)",
        max_length=20,
    )

    # API cost in USD
    cost: Optional[float] = Field(
        default=None,
        description="Phase 5.2 reserved: API cost in USD (not implemented)",
        ge=0,
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