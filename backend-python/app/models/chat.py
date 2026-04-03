"""Chat API request/response models.

Defines schemas for:
- Chat streaming requests with session and context
- User confirmation requests for dangerous operations
- SSE event types and data structures
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatStreamRequest(BaseModel):
    """Request for chat streaming endpoint."""

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID (creates new session if None)",
    )
    message: str = Field(
        ...,
        description="User message",
        min_length=1,
        max_length=10000,
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (paper_ids, auto_confirm, etc.)",
    )


class ChatConfirmRequest(BaseModel):
    """Request for user confirmation endpoint."""

    confirmation_id: str = Field(
        ...,
        description="Unique confirmation ID",
    )
    approved: bool = Field(
        ...,
        description="Whether user approved the action",
    )
    session_id: str = Field(
        ...,
        description="Session ID to resume execution",
    )


class SSEEvent(BaseModel):
    """Server-Sent Event structure."""

    event: str = Field(
        ...,
        description="Event type (thought, tool_call, tool_result, message, etc.)",
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event data payload",
    )


# SSE Event Types
class SSEEventType:
    """Constants for SSE event types."""

    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CONFIRMATION_REQUIRED = "confirmation_required"
    MESSAGE = "message"
    ERROR = "error"
    DONE = "done"
    HEARTBEAT = "heartbeat"


class ThoughtEventData(BaseModel):
    """Data for 'thought' SSE event."""

    type: str = Field(default="thinking", description="Thought type")
    content: str = Field(..., description="Thought content")


class ToolCallEventData(BaseModel):
    """Data for 'tool_call' SSE event."""

    type: str = Field(default="tool_call", description="Event type")
    tool: str = Field(..., description="Tool name")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")


class ToolResultEventData(BaseModel):
    """Data for 'tool_result' SSE event."""

    type: str = Field(default="tool_result", description="Event type")
    tool: str = Field(..., description="Tool name")
    success: bool = Field(..., description="Whether tool execution succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Tool result data")
    error: Optional[str] = Field(None, description="Error message if failed")


class ConfirmationRequiredEventData(BaseModel):
    """Data for 'confirmation_required' SSE event."""

    type: str = Field(default="confirmation_required", description="Event type")
    confirmation_id: str = Field(..., description="Unique confirmation ID")
    message: str = Field(..., description="Confirmation message for user")
    tool_name: str = Field(..., description="Tool requiring confirmation")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")


class MessageEventData(BaseModel):
    """Data for 'message' SSE event (final response)."""

    type: str = Field(default="message", description="Event type")
    content: str = Field(..., description="Message content")


class ErrorEventData(BaseModel):
    """Data for 'error' SSE event."""

    type: str = Field(default="error", description="Event type")
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")