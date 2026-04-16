"""Confirmation state models for dangerous tool approval.

Provides:
- ConfirmationState: Redis-stored confirmation state
- ConfirmationRequest: User confirmation request

Per Sprint 3: Confirmation mechanism closure.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


class ConfirmationState(BaseModel):
    """Confirmation state stored in Redis.

    Redis key: confirmation:{confirmation_id}
    TTL: 1 hour (3600 seconds)

    Fields:
        - confirmation_id: Unique identifier for this confirmation
        - session_id: Session ID for resuming Agent
        - user_id: User ID for ownership validation
        - tool_name: Tool requiring confirmation
        - parameters: Tool execution parameters
        - status: pending/approved/rejected/expired
        - created_at: Creation timestamp
        - expires_at: Expiration timestamp
    """

    confirmation_id: str = Field(
        ...,
        description="Unique confirmation ID",
    )
    session_id: str = Field(
        ...,
        description="Session ID for Agent resumption",
    )
    user_id: str = Field(
        ...,
        description="User ID for ownership validation",
    )
    tool_name: str = Field(
        ...,
        description="Tool requiring confirmation",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool parameters",
    )
    status: str = Field(
        default="pending",
        description="Confirmation status: pending/approved/rejected/expired",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    expires_at: datetime = Field(
        ...,
        description="Expiration timestamp",
    )

    def is_expired(self) -> bool:
        """Check if confirmation has expired.

        Returns:
            True if current time > expires_at
        """
        return datetime.now(timezone.utc) > self.expires_at


class ConfirmationRequest(BaseModel):
    """User confirmation request for resuming Agent.

    Matches ChatConfirmRequest in chat.py for backend compatibility.
    """

    confirmation_id: str = Field(
        ...,
        description="Confirmation ID from SSE event",
    )
    session_id: str = Field(
        ...,
        description="Session ID",
    )
    approved: bool = Field(
        ...,
        description="Whether user approved the tool execution",
    )
