"""Authentication API routes.

Provides OAuth 2.0 + Cookie-based authentication endpoints:
- POST /register - Create new user account
- POST /login - Authenticate and set cookies
- POST /refresh - Rotate refresh tokens
- POST /logout - Blacklist tokens and clear cookies
- GET /me - Get current user info

All endpoints use RFC 7807 Problem Details for error responses.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
import re

from app.deps import get_current_user
from app.services.auth_service import (
    User,
    register_user,
    authenticate_user,
    create_user_tokens,
    refresh_access_token,
    logout_user,
)
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


router = APIRouter(tags=["Authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: str
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=50)

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        """Validate email format."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password has required complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    """User login request."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        """Validate email format."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class UserResponse(BaseModel):
    """User data in responses."""

    id: str
    email: str
    name: str
    email_verified: bool = False
    avatar: Optional[str] = None
    roles: list[str] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication success response."""

    success: bool = True
    data: dict


class RefreshRequest(BaseModel):
    """Token refresh request (optional body, cookie preferred)."""

    refresh_token: Optional[str] = None


# =============================================================================
# Cookie Settings
# =============================================================================

# Cookie configuration
ACCESS_TOKEN_MAX_AGE = 60 * 60  # 1 hour
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def get_cookie_settings() -> dict:
    """Get cookie settings based on environment.

    Returns:
        Cookie settings dict with secure flag based on ENVIRONMENT
    """
    from app.config import settings

    return {
        "httponly": True,
        "secure": settings.ENVIRONMENT == "production",  # HTTPS required in production
        "samesite": "lax",
        "path": "/",
    }


COOKIE_SETTINGS = get_cookie_settings()


def _create_error_response(
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


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: Request,
    body: RegisterRequest,
):
    """Register a new user account.

    Creates a new user with default 'user' role.

    Returns:
        User data without sensitive information.

    Raises:
        400: Validation error (password too weak, invalid email)
        409: Email already registered
    """
    instance = str(request.url.path)
    request_id = str(uuid4())

    try:
        user = await register_user(
            email=body.email,
            password=body.password,
            name=body.name,
        )

        logger.info(
            "User registered",
            user_id=user.id,
            email=user.email,
            request_id=request_id,
        )

        return AuthResponse(
            success=True,
            data={
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "email_verified": user.email_verified,
                    "roles": user.roles,
                    "created_at": user.created_at.isoformat()
                    if user.created_at
                    else None,
                },
                "meta": {
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    except ValueError as e:
        error_msg = str(e)
        if "already registered" in error_msg:
            raise _create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                error_type=ErrorTypes.CONFLICT,
                title="Conflict",
                detail=error_msg,
                instance=instance,
            )
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail=error_msg,
            instance=instance,
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate user and set httpOnly cookies.

    Uses OAuth2 password flow (form-data: username=email, password).

    Sets cookies:
        - accessToken: JWT for API authentication (1 hour)
        - refreshToken: JWT for token refresh (7 days)

    Returns:
        User data without sensitive information.

    Raises:
        400: Validation error
        401: Invalid credentials
    """
    instance = str(request.url.path)
    request_id = str(uuid4())

    # Authenticate user (form_data.username is the email in OAuth2)
    user = await authenticate_user(
        email=form_data.username,
        password=form_data.password,
    )

    if not user:
        raise _create_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.INVALID_CREDENTIALS,
            title="Invalid Credentials",
            detail="Email or password is incorrect",
            instance=instance,
        )

    # Create tokens
    tokens = await create_user_tokens(user)

    # Set httpOnly cookies
    response.set_cookie(
        key="accessToken",
        value=tokens["access_token"],
        max_age=ACCESS_TOKEN_MAX_AGE,
        **COOKIE_SETTINGS,
    )
    response.set_cookie(
        key="refreshToken",
        value=tokens["refresh_token"],
        max_age=REFRESH_TOKEN_MAX_AGE,
        **COOKIE_SETTINGS,
    )

    logger.info(
        "User logged in",
        user_id=user.id,
        email=user.email,
        request_id=request_id,
    )

    return AuthResponse(
        success=True,
        data={
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "email_verified": user.email_verified,
                "avatar": user.avatar,
                "roles": user.roles,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: Request,
    response: Response,
    body: Optional[RefreshRequest] = None,
):
    """Refresh access token using refresh token.

    Reads refresh token from cookie (preferred) or request body.
    Rotates refresh token (old one is blacklisted).

    Returns:
        Success message.

    Raises:
        401: Invalid or expired refresh token
    """
    instance = str(request.url.path)
    request_id = str(uuid4())

    # Get refresh token from cookie or body
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token and body:
        refresh_token = body.refresh_token

    if not refresh_token:
        raise _create_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.UNAUTHORIZED,
            title="Unauthorized",
            detail="Refresh token required",
            instance=instance,
        )

    try:
        # Refresh tokens
        new_tokens = await refresh_access_token(refresh_token)

        # Set new cookies
        response.set_cookie(
            key="accessToken",
            value=new_tokens["access_token"],
            max_age=ACCESS_TOKEN_MAX_AGE,
            **COOKIE_SETTINGS,
        )
        response.set_cookie(
            key="refreshToken",
            value=new_tokens["refresh_token"],
            max_age=REFRESH_TOKEN_MAX_AGE,
            **COOKIE_SETTINGS,
        )

        logger.info(
            "Token refreshed",
            request_id=request_id,
        )

        return AuthResponse(
            success=True,
            data={
                "message": "Token refreshed successfully",
                "meta": {
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    except ValueError as e:
        raise _create_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type=ErrorTypes.UNAUTHORIZED,
            title="Unauthorized",
            detail=str(e),
            instance=instance,
        )


@router.post("/logout", response_model=AuthResponse)
async def logout(
    request: Request,
    response: Response,
):
    """Logout user and blacklist tokens.

    Blacklists both access and refresh tokens in Redis.
    Clears cookies.

    Returns:
        Success message.
    """
    request_id = str(uuid4())

    # Get tokens from cookies
    access_token = request.cookies.get("accessToken")
    refresh_token = request.cookies.get("refreshToken")

    # Blacklist tokens
    await logout_user(access_token, refresh_token)

    # Clear cookies
    response.delete_cookie(
        key="accessToken",
        path=COOKIE_SETTINGS["path"],
    )
    response.delete_cookie(
        key="refreshToken",
        path=COOKIE_SETTINGS["path"],
    )

    logger.info(
        "User logged out",
        request_id=request_id,
    )

    return AuthResponse(
        success=True,
        data={
            "message": "Logged out successfully",
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


@router.get("/me", response_model=AuthResponse)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user info.

    Requires valid authentication via cookie or Authorization header.

    Returns:
        User data.

    Raises:
        401: Not authenticated
    """
    request_id = str(uuid4())

    return AuthResponse(
        success=True,
        data={
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "email_verified": current_user.email_verified,
            "avatar": current_user.avatar,
            "roles": current_user.roles,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: Request,
    body: dict,
):
    """Request password reset email.

    Always returns success to prevent email enumeration.
    For MVP, logs the reset link instead of sending email.

    Returns:
        Success message.
    """
    email = body.get("email")

    if not email:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Email is required",
            instance=str(request.url.path),
        )

    # For MVP, just log that this was requested
    # In production, would send email with reset link
    logger.info(
        "Password reset requested",
        email=email,
    )

    return AuthResponse(
        success=True,
        data={
            "message": "If the email exists, a reset link has been sent",
        },
    )


__all__ = ["router"]
