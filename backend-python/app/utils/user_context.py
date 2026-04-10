"""User context extraction from Cookie-based auth or X-User-ID header.

Supports two authentication modes:
1. Cookie-based: JWT token in accessToken cookie (primary, for direct frontend access)
2. X-User-ID header: Pass-through from API gateway (secondary, for internal services)

Architecture:
    Frontend → Python Service (Cookie JWT validation)
    API Gateway → Python Service (X-User-ID header)
"""

from typing import Optional

from fastapi import Header, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer

from app.utils.problem_detail import ErrorTypes, create_error
from app.utils.security import verify_token
from app.utils.logger import logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    token: Optional[str] = Depends(oauth2_scheme),
) -> str:
    """
    Extract user ID from Cookie-based auth or X-User-ID header.

    Priority:
    1. X-User-ID header (from API gateway)
    2. Cookie (accessToken) - most common for direct frontend access
    3. Authorization header (Bearer token) - fallback

    Args:
        request: FastAPI request object
        x_user_id: User ID from X-User-ID header
        token: Optional token from OAuth2 scheme (Authorization header)

    Returns:
        Verified user UUID string

    Raises:
        HTTPException: 401 Unauthorized if authentication fails
    """
    # Priority 1: X-User-ID header (from API gateway)
    if x_user_id:
        return x_user_id

    # Priority 2: Cookie (accessToken)
    access_token = request.cookies.get("accessToken") or token

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail=create_error(
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                status=401,
                detail="Authentication required. Please log in."
            )
        )

    try:
        # Verify JWT token
        payload = verify_token(access_token, "access")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail=create_error(
                    error_type=ErrorTypes.UNAUTHORIZED,
                    title="Unauthorized",
                    status=401,
                    detail="Invalid token. Please log in again."
                )
            )

        return user_id

    except ValueError as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=create_error(
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                status=401,
                detail="Invalid token. Please log in again."
            )
        )


async def require_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    token: Optional[str] = Depends(oauth2_scheme),
) -> str:
    """
    Alias for get_current_user_id for backwards compatibility.

    Args:
        request: FastAPI request object
        x_user_id: User ID from X-User-ID header
        token: Optional token from OAuth2 scheme

    Returns:
        Verified user UUID string

    Raises:
        HTTPException: 401 Unauthorized if authentication fails
    """
    return await get_current_user_id(request, x_user_id, token)