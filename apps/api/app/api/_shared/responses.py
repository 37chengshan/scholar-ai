"""Shared response models for API endpoints.

Provides common response wrappers used across multiple modules:
- MessageResponse / MessageData: Simple CRUD operations (DELETE, etc.)
- DeleteResponse / DeleteData: Entity deletion with ID
- OperationResponse / OperationData: Generic operation result
"""

from pydantic import BaseModel


class MessageData(BaseModel):
    """Message data structure."""

    message: str


class MessageResponse(BaseModel):
    """Simple message response wrapper."""

    success: bool = True
    data: MessageData


class DeleteData(BaseModel):
    """Deletion result data."""

    id: str
    deleted: bool = True


class DeleteResponse(BaseModel):
    """Delete operation response wrapper."""

    success: bool = True
    data: DeleteData


class OperationData(BaseModel):
    """Generic operation result data."""

    id: str
    operation: str
    success: bool = True


class OperationResponse(BaseModel):
    """Generic operation response wrapper."""

    success: bool = True
    data: OperationData


__all__ = [
    "MessageData",
    "MessageResponse",
    "DeleteData",
    "DeleteResponse",
    "OperationData",
    "OperationResponse",
]
