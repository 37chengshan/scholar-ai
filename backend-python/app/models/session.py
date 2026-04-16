"""Deprecated import shim for session schemas.

Use app.schemas.session for new imports.
"""

from app.schemas.session import (
    SessionBase,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)

__all__ = [
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
]
