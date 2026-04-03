"""Session management API endpoints.

Provides RESTful endpoints for Session CRUD operations:
- POST /api/sessions: Create new session
- GET /api/sessions: List user's sessions
- GET /api/sessions/{session_id}: Get specific session
- PATCH /api/sessions/{session_id}: Update session
- DELETE /api/sessions/{session_id}: Delete session
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Header

from app.models.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
)
from app.utils.session_manager import session_manager
from app.utils.logger import logger

router = APIRouter()


# =============================================================================
# Authentication Helper (placeholder - implement based on your auth system)
# =============================================================================

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from JWT token.

    TODO: Implement actual JWT validation
    For now, extract user_id from a test header or return a test user.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User UUID

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        # For development/testing, return a test user ID
        # TODO: Remove this in production and enforce authentication
        logger.warning("No authorization header - using test user")
        return "00000000-0000-0000-0000-000000000001"

    # TODO: Implement JWT validation
    # For now, just extract user_id from token payload
    # This is a placeholder - implement proper JWT validation
    try:
        # Placeholder: In real implementation, decode and validate JWT
        # user_id = decode_jwt_token(authorization.replace("Bearer ", ""))
        # return user_id

        # For now, return test user
        return "00000000-0000-0000-0000-000000000001"

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# =============================================================================
# Session CRUD Endpoints
# =============================================================================

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new conversation session with optional title. Session expires after 30 days."
)
async def create_session(
    session_data: SessionCreate,
    user_id: str = Header(None, alias="X-User-ID")  # Temporarily use header for testing
):
    """
    Create a new session.

    Args:
        session_data: Session creation data (title, status, metadata)
        user_id: Authenticated user ID

    Returns:
        Created session with all fields
    """
    try:
        # Get user ID (use header for now, will use JWT later)
        if not user_id:
            user_id = await get_current_user_id()

        session = await session_manager.create_session(
            user_id=user_id,
            title=session_data.title
        )

        logger.info(f"Created session {session.id} via API")
        return session

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List user's sessions",
    description="List all active sessions for the authenticated user, ordered by last activity."
)
async def list_sessions(
    limit: int = 20,
    status: str = "active",
    user_id: str = Header(None, alias="X-User-ID")
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
        if not user_id:
            user_id = await get_current_user_id()

        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )

        sessions = await session_manager.list_user_sessions(
            user_id=user_id,
            limit=limit,
            status=status
        )

        return SessionListResponse(
            sessions=sessions,
            total=len(sessions),
            limit=limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a specific session",
    description="Retrieve session details by ID. Returns 404 if session not found or not owned by user."
)
async def get_session(
    session_id: str,
    user_id: str = Header(None, alias="X-User-ID")
):
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
        if not user_id:
            user_id = await get_current_user_id()

        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Verify ownership
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session"
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Update a session",
    description="Update session fields (title, status, metadata). Returns 404 if session not found."
)
async def update_session(
    session_id: str,
    updates: SessionUpdate,
    user_id: str = Header(None, alias="X-User-ID")
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
        if not user_id:
            user_id = await get_current_user_id()

        # Check ownership first
        existing = await session_manager.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        if existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this session"
            )

        # Update session
        updated = await session_manager.update_session(session_id, updates)

        logger.info(f"Updated session {session_id} via API")
        return updated

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    description="Delete a session and all its messages. This action cannot be undone."
)
async def delete_session(
    session_id: str,
    user_id: str = Header(None, alias="X-User-ID")
):
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
        if not user_id:
            user_id = await get_current_user_id()

        # Check ownership first
        existing = await session_manager.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        if existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this session"
            )

        # Delete session
        success = await session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session"
            )

        logger.info(f"Deleted session {session_id} via API")
        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )