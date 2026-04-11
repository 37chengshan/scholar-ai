"""Session management API endpoints.

Provides RESTful endpoints for Session CRUD operations:
- POST /api/sessions: Create new session
- GET /api/sessions: List user's sessions
- GET /api/sessions/{session_id}: Get specific session
- PATCH /api/sessions/{session_id}: Update session
- DELETE /api/sessions/{session_id}: Delete session
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.models.session import (
    SessionCreate,
    SessionUpdate,
)
from app.utils.session_manager import session_manager
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class SessionResponse(BaseModel):
    """Response wrapper for session endpoints."""

    success: bool = True
    data: Dict[str, Any]


class SessionListResponse(BaseModel):
    """Response wrapper for sessions list."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Helper Functions
# =============================================================================


def _format_session_response(session) -> dict:
    """Format session for API response with camelCase fields."""
    return {
        "id": session.id,
        "userId": session.user_id,
        "title": session.title,
        "status": session.status,
        "metadata": session.session_metadata
        if hasattr(session, "session_metadata")
        else session.metadata,
        "messageCount": session.message_count,
        "toolCallCount": session.tool_call_count,
        "createdAt": session.created_at.isoformat() if session.created_at else None,
        "updatedAt": session.updated_at.isoformat() if session.updated_at else None,
        "lastActivityAt": session.last_activity_at.isoformat()
        if session.last_activity_at
        else None,
        "expiresAt": session.expires_at.isoformat() if session.expires_at else None,
    }


# =============================================================================
# Session CRUD Endpoints
# =============================================================================


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new conversation session with optional title. Session expires after 30 days.",
)
async def create_session(session_data: SessionCreate, user_id: str = CurrentUserId):
    """
    Create a new session.

    Args:
        session_data: Session creation data (title, status, metadata)
        user_id: Authenticated user ID

    Returns:
        Created session with all fields
    """
    try:
session = await session_manager.create_session(
            user_id=user_id,
            title=session_data.title
        )

        logger.info(f"Created session {session.id} via API")
        return SessionResponse(
            success=True,
            data=_format_session_response(session)
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create session: {str(e)}"),
        )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List user's sessions",
    description="List all active sessions for the authenticated user, ordered by last activity.",
)
async def list_sessions(
    limit: int = 20, status: str = "active", user_id: str = CurrentUserId
):
    """
    List user's sessions.

    Query params:
        limit: Maximum number of sessions to return (default 20, max 100)
        status: Filter by status (active, archived, deleted)

    Returns:
        Paginated list of sessions
    """
    try:
        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Limit must be between 1 and 100"),
            )

sessions = await session_manager.list_user_sessions(
            user_id=user_id,
            limit=limit,
            status=status
        )

        return SessionListResponse(
            success=True,
            data={
                "sessions": [_format_session_response(s) for s in sessions],
                "total": len(sessions),
                "limit": limit,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list sessions: {str(e)}"),
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a specific session",
    description="Retrieve session details by ID. Returns 404 if session not found or not owned by user.",
)
async def get_session(session_id: str, user_id: str = CurrentUserId):
    """
    Get a specific session by ID.

    Args:
        session_id: Session UUID
        user_id: Authenticated user ID

    Returns:
        Session details

    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    try:
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"Session {session_id} not found"),
            )

# Verify ownership
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden("You don't have permission to access this session")
            )

        return SessionResponse(
            success=True,
            data=_format_session_response(session)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get session: {str(e)}"),
        )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Update a session",
    description="Update session fields (title, status, metadata). Returns 404 if session not found.",
)
async def update_session(
    session_id: str, updates: SessionUpdate, user_id: str = CurrentUserId
):
    """
    Update a session.

    Args:
        session_id: Session UUID
        updates: Fields to update (partial update)
        user_id: Authenticated user ID

    Returns:
        Updated session

    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    try:
        # Check ownership first
        existing = await session_manager.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"Session {session_id} not found"),
            )

        if existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden(
                    "You don't have permission to update this session"
                ),
            )

        # Update session
        updated = await session_manager.update_session(session_id, updates)

        logger.info(f"Updated session {session_id} via API")
        return SessionResponse(
            success=True,
            data=_format_session_response(updated)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update session: {str(e)}"),
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    description="Delete a session and all its messages. This action cannot be undone.",
)
async def delete_session(session_id: str, user_id: str = CurrentUserId):
    """
    Delete a session.

    Args:
        session_id: Session UUID
        user_id: Authenticated user ID

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
    try:
        # Check ownership first
        existing = await session_manager.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"Session {session_id} not found"),
            )

        if existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden(
                    "You don't have permission to delete this session"
                ),
            )

        # Delete session
        success = await session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=Errors.internal("Failed to delete session"),
            )

        logger.info(f"Deleted session {session_id} via API")
        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete session: {str(e)}"),
        )
