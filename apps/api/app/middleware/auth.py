"""Authentication middleware for FastAPI.

Provides OAuth 2.0 + Cookie-based authentication:
- OAuth2PasswordBearer scheme for OpenAPI docs
- get_current_user dependency for protected routes
- Cookie-first token extraction with header fallback

Usage:
    from app.middleware.auth import get_current_user, oauth2_scheme

    @router.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": user.id}
"""

from typing import Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.database import redis_db
from app.services.auth_service import User, get_user_by_id
from app.utils.security import verify_token
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger, bind_request_context


# OAuth2 scheme for OpenAPI documentation and Authorization header fallback
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


class TokenData:
    """Token payload data."""

    def __init__(
        self,
        sub: str,
        email: Optional[str] = None,
        roles: Optional[list] = None,
        jti: Optional[str] = None,
    ):
        self.sub = sub
        self.email = email
        self.roles = roles or []
        self.jti = jti


def _create_auth_error(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    instance: str,
) -> HTTPException:
    """Create HTTPException with RFC 7807 ProblemDetail."""
    problem = ProblemDetail(
        type=error_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
    )
    return HTTPException(
        status_code=status_code,
        detail=problem.to_dict(),
    )


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """Extract and validate user from cookie or Authorization header.

    Priority:
    1. Cookie (accessToken) - most secure, httpOnly
    2. Authorization header (Bearer token) - fallback

    Args:
        request: FastAPI request object
        token: Optional token from OAuth2 scheme (header)

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If not authenticated or token invalid
    """
    request_id = str(uuid4())
    instance = str(request.url.path)

    # Priority 1: Cookie (most secure)
    token = request.cookies.get("accessToken") or token

    if not token:
        logger.warning(
            "No authentication token provided",
            path=instance,
            request_id=request_id,
        )
        raise _create_auth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.UNAUTHORIZED,
            title="Unauthorized",
            detail="Authentication required. Please log in.",
            instance=instance,
        )

    try:
        # Verify token
        payload = verify_token(token, "access")

        # Extract claims
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id:
            logger.warning(
                "Token missing sub claim",
                path=instance,
                request_id=request_id,
            )
            raise _create_auth_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid token. Please log in again.",
                instance=instance,
            )

        request.state.user_id = user_id
        request_id_for_bind = getattr(request.state, "request_id", None) or request.headers.get(
            "X-Request-ID"
        )
        if request_id_for_bind:
            bind_request_context(
                request_id=request_id_for_bind,
                route=getattr(request.state, "route", instance),
                user_id=user_id,
            )

        # Check blacklist in Redis
        redis_client = redis_db.client
        if not redis_client:
            logger.error(
                "Redis unavailable during auth verification (fail-closed)",
                user_id=user_id,
                path=instance,
                request_id=request_id,
            )
            raise _create_auth_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_type=ErrorTypes.SERVICE_UNAVAILABLE,
                title="Service Unavailable",
                detail="Authentication service is temporarily unavailable.",
                instance=instance,
            )

        if jti:
            is_blacklisted = await redis_client.exists(f"blacklist:{jti}")
            if is_blacklisted:
                logger.warning(
                    "Blacklisted token used",
                    jti=jti,
                    user_id=user_id,
                    path=instance,
                    request_id=request_id,
                )
                raise _create_auth_error(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    error_type=ErrorTypes.UNAUTHORIZED,
                    title="Unauthorized",
                    detail="Token has been revoked. Please log in again.",
                    instance=instance,
                )

        # Get user from database
        user = await get_user_by_id(user_id)
        if not user:
            logger.warning(
                "User not found",
                user_id=user_id,
                path=instance,
                request_id=request_id,
            )
            raise _create_auth_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_type=ErrorTypes.UNAUTHORIZED,
                title="Unauthorized",
                detail="User not found. Please log in again.",
                instance=instance,
            )

        return user

    except ValueError as e:
        # Token verification failed
        logger.warning(
            "Token verification failed",
            error=str(e),
            path=instance,
            request_id=request_id,
        )
        raise _create_auth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.UNAUTHORIZED,
            title="Unauthorized",
            detail="Invalid token. Please log in again.",
            instance=instance,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during authentication",
            error=str(e),
            path=instance,
            request_id=request_id,
        )
        raise _create_auth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.UNAUTHORIZED,
            title="Unauthorized",
            detail="Authentication failed. Please log in again.",
            instance=instance,
        )


async def get_current_user_id(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> str:
    """Lightweight authentication returning user_id string.

    Includes blacklist check for revoked tokens.
    Uses get_current_user internally to ensure consistent validation.

    Args:
        request: FastAPI request object
        token: Optional token from OAuth2 scheme (header)

    Returns:
        user_id string if authenticated

    Raises:
        HTTPException: If not authenticated or token invalid/revoked
    """
    user = await get_current_user(request, token)
    return user.id


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is active.

    Currently all users are considered active.
    Can be extended to check email_verified, status, etc.

    Args:
        current_user: User from get_current_user

    Returns:
        User if active

    Raises:
        HTTPException: If user is not active
    """
    # For MVP, all users are considered active
    # Can add email_verified check here if needed
    return current_user


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """Optionally extract user from token without requiring authentication.

    Use for routes that have different behavior for authenticated vs
    unauthenticated users.

    Args:
        request: FastAPI request object
        token: Optional token from OAuth2 scheme

    Returns:
        User object if authenticated, None otherwise
    """
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None


def require_roles(*required_roles: str):
    """Create a dependency that requires specific roles.

    Usage:
        @router.get("/admin")
        async def admin_route(
            user: User = Depends(require_roles("admin"))
        ):
            return {"message": "Admin access"}

    Args:
        required_roles: Role names required for access

    Returns:
        Dependency function that validates roles
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not any(role in current_user.roles for role in required_roles):
            raise _create_auth_error(
                status_code=status.HTTP_403_FORBIDDEN,
                error_type=ErrorTypes.FORBIDDEN,
                title="Forbidden",
                detail=f"Required role: {', '.join(required_roles)}",
                instance="",
            )
        return current_user

    return role_checker


# =============================================================================
# Unified Authentication Dependencies
# =============================================================================

# Primary dependency for protected routes - returns User object
CurrentUser = Depends(get_current_user)

# Lightweight dependency - returns user_id string (with blacklist check)
CurrentUserId = Depends(get_current_user_id)


__all__ = [
    "oauth2_scheme",
    "get_current_user",
    "get_current_user_id",
    "get_current_active_user",
    "get_optional_user",
    "require_roles",
    "TokenData",
    "CurrentUser",
    "CurrentUserId",
]
