"""User context extraction from X-User-ID header.

Node.js API Gateway validates JWT and passes verified user_id to Python service
via X-User-ID header. This module provides FastAPI dependencies for extracting
the authenticated user_id.

Architecture:
    Client → Node.js Gateway (JWT validation) → Python Service (X-User-ID header)

Security:
    - Node.js performs full JWT validation (signature, expiration, blacklist)
    - Python trusts X-User-ID header from Node.js only
    - No JWT validation in Python service (per D-01 decision)
"""

from fastapi import Header, HTTPException

from app.utils.problem_detail import ErrorTypes, create_error


async def get_current_user_id(x_user_id: str | None = Header(None, alias="X-User-ID")) -> str:
    """
    Extract user ID from X-User-ID header set by Node.js gateway.

    Node.js validates JWT and passes verified user_id to Python service.
    This dependency enforces that the header must be present and non-empty.

    Args:
        x_user_id: User ID extracted from X-User-ID header (injected by FastAPI)

    Returns:
        Verified user UUID string

    Raises:
        HTTPException: 401 Unauthorized if header is missing or empty

    Example:
        @router.get("/protected")
        async def protected_endpoint(user_id: str = Depends(get_current_user_id)):
            # user_id is guaranteed to be a valid, authenticated user UUID
            return {"user_id": user_id}
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail=create_error(
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                status=401,
                detail="Authentication required. X-User-ID header is missing or empty."
            )
        )
    return x_user_id


async def require_user_id(user_id: str | None = Header(None, alias="X-User-ID")) -> str:
    """
    Alias for get_current_user_id for backwards compatibility.

    This is a convenience function that wraps get_current_user_id.
    Can be used interchangeably with get_current_user_id.

    Args:
        user_id: User ID from X-User-ID header

    Returns:
        Verified user UUID string

    Raises:
        HTTPException: 401 Unauthorized if header is missing or empty
    """
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=create_error(
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                status=401,
                detail="Authentication required. Please log in."
            )
        )
    return user_id