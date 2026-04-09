"""Users API routes.

Provides user management endpoints:
- GET /me - Get current user profile
- PATCH /me - Update user profile
- POST /me/avatar - Upload avatar
- PATCH /me/password - Change password
- GET /me/settings - Get user settings
- PATCH /me/settings - Update user settings
- GET /me/api-keys - List API keys
- POST /me/api-keys - Create API key
- DELETE /me/api-keys/:id - Delete API key

All endpoints use RFC 7807 Problem Details for error responses.
Per D-04: Modular route organization.
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User, ApiKey, RefreshToken
from app.services.auth_service import get_user_by_id
from app.services.storage_service import get_storage_service
from app.utils.security import get_password_hash, verify_password
from app.utils.problem_detail import ProblemDetail, ErrorTypes, create_error
from app.utils.logger import logger


router = APIRouter(tags=["Users"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UserProfileResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    name: str
    avatar: Optional[str] = None
    email_verified: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import re
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
                raise ValueError('Invalid email format')
            return v.lower()
        return v


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class SettingsResponse(BaseModel):
    """User settings response."""
    language: str = "zh"
    defaultModel: str = "glm-4-flash"
    theme: str = "light"


class SettingsUpdateRequest(BaseModel):
    """Settings update request."""
    language: Optional[str] = None
    defaultModel: Optional[str] = None
    theme: Optional[str] = None

    @field_validator('language')
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["zh", "en"]:
            raise ValueError('Invalid language. Allowed: zh, en')
        return v

    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["light", "dark"]:
            raise ValueError('Invalid theme. Allowed: light, dark')
        return v


class ApiKeyResponse(BaseModel):
    """API key response."""
    id: str
    name: str
    prefix: Optional[str] = None
    created_at: Optional[str] = None
    key: Optional[str] = None  # Only present on creation


class ApiKeyCreateRequest(BaseModel):
    """API key create request."""
    name: str = Field(..., min_length=1, max_length=100)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Helper Functions
# =============================================================================

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


def _generate_api_key() -> str:
    """Generate API key in sk_live_xxxx format."""
    random_bytes = secrets.token_urlsafe(32)
    return f"sk_live_{random_bytes}"


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/me", response_model=SuccessResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile.

    Returns:
        User profile data.

    Raises:
        401: Not authenticated
    """
    return SuccessResponse(
        success=True,
        data={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar": current_user.avatar,
            "email_verified": current_user.email_verified,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
    )


@router.patch("/me", response_model=SuccessResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile.

    Args:
        body: Profile update data (name, email, avatar)

    Returns:
        Updated user profile.

    Raises:
        400: No fields to update
        409: Email already in use
    """
    # Validate at least one field provided
    if not any([body.name, body.email, body.avatar]):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="At least one field (name, email, avatar) required",
            instance="/api/v1/users/me",
        )

    # Build update object
    updates = {}
    if body.name:
        updates["name"] = body.name
    if body.email:
        # Check email uniqueness
        result = await db.execute(
            select(User).where(User.email == body.email, User.id != current_user.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise _create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                error_type=ErrorTypes.CONFLICT,
                title="Conflict",
                detail="Email already in use",
                instance="/api/v1/users/me",
            )
        updates["email"] = body.email
    if body.avatar:
        updates["avatar"] = body.avatar

    # Update user
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.execute(
            update(User).where(User.id == current_user.id).values(**updates)
        )

    logger.info("Profile updated", user_id=current_user.id, fields=list(updates.keys()))

    # Get updated user
    result = await db.execute(select(User).where(User.id == current_user.id))
    updated_user = result.scalar_one_or_none()

    return SuccessResponse(
        success=True,
        data={
            "id": updated_user.id,
            "email": updated_user.email,
            "name": updated_user.name,
            "avatar": updated_user.avatar,
        },
    )


@router.post("/me/avatar", response_model=SuccessResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload avatar image.

    Args:
        file: Avatar image file (JPEG, PNG, WebP)

    Returns:
        Avatar URL.

    Raises:
        400: Invalid file type or missing file
        413: File too large (max 5MB)
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Invalid file type. Allowed: JPEG, PNG, WebP",
            instance="/api/v1/users/me/avatar",
        )

    # Read file content
    content = await file.read()

    # Validate file size (5MB max)
    if len(content) > 5 * 1024 * 1024:
        raise _create_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="File Too Large",
            detail="Avatar file must be less than 5MB",
            instance="/api/v1/users/me/avatar",
        )

    # Generate storage key
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    storage_key = f"avatars/{current_user.id}-{int(datetime.now(timezone.utc).timestamp())}.{ext}"

    # Upload to storage
    storage = get_storage_service()
    await storage.upload_file(content, storage_key, file.content_type)

    # Get URL
    avatar_url = await storage.get_file_url(storage_key)

    # Update user avatar
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(avatar=storage_key, updated_at=datetime.now(timezone.utc))
    )

    logger.info("Avatar uploaded", user_id=current_user.id, storage_key=storage_key)

    return SuccessResponse(
        success=True,
        data={"avatar": avatar_url},
    )


@router.get("/me/settings", response_model=SuccessResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user settings.

    Returns:
        User settings JSON.
    """
    # Get user with settings
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    # Default settings if null
    settings_data = user.settings if user and user.settings else None
    if not settings_data:
        settings_data = {
            "language": "zh",
            "defaultModel": "glm-4-flash",
            "theme": "light",
        }

    return SuccessResponse(
        success=True,
        data=settings_data,
    )


@router.patch("/me/settings", response_model=SuccessResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings.

    Args:
        body: Settings update data

    Returns:
        Updated settings.
    """
    # Get current settings
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    current_settings = user.settings if user else {}
    if not isinstance(current_settings, dict):
        current_settings = {}

    # Default settings
    default_settings = {
        "language": "zh",
        "defaultModel": "glm-4-flash",
        "theme": "light",
    }

    # Merge with defaults
    merged = {**default_settings, **current_settings}

    # Apply updates
    if body.language:
        merged["language"] = body.language
    if body.defaultModel:
        merged["defaultModel"] = body.defaultModel
    if body.theme:
        merged["theme"] = body.theme

    # Save settings
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(settings=merged, updated_at=datetime.now(timezone.utc))
    )

    logger.info("Settings updated", user_id=current_user.id, settings=merged)

    return SuccessResponse(
        success=True,
        data=merged,
    )


@router.patch("/me/password", response_model=SuccessResponse)
async def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password.

    Requires current password verification.

    Args:
        body: Password change data

    Returns:
        Success message.

    Raises:
        400: Invalid current password
    """
    # Get user with password hash
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="User not found",
            instance="/api/v1/users/me/password",
        )

    # Verify current password
    if not verify_password(body.current_password, user.password_hash):
        raise _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            detail="Current password is incorrect",
            instance="/api/v1/users/me/password",
        )

    # Hash new password
    new_hash = get_password_hash(body.new_password)

    # Update password
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(password_hash=new_hash, updated_at=datetime.now(timezone.utc))
    )

    # Invalidate all refresh tokens (security measure)
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == current_user.id))

    logger.info("Password changed", user_id=current_user.id)

    return SuccessResponse(
        success=True,
        data={"message": "Password changed successfully. Please log in again."},
    )


@router.get("/me/api-keys", response_model=SuccessResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's API keys.

    Returns:
        List of API keys (without the full key).
    """
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    api_keys_objs = result.scalars().all()

    api_keys = [
        {
            "id": key.id,
            "name": key.name,
            "prefix": key.prefix,
            "createdAt": key.created_at.isoformat() if key.created_at else None,
            "lastUsedAt": key.last_used_at.isoformat() if key.last_used_at else None,
        }
        for key in api_keys_objs
    ]

    logger.info("API keys listed", user_id=current_user.id, count=len(api_keys))

    return SuccessResponse(
        success=True,
        data=api_keys,
    )


@router.post("/me/api-keys", response_model=SuccessResponse)
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new API key.

    Args:
        body: API key creation data (name)

    Returns:
        Created API key with full key (shown once!).

    Note:
        The full key is only shown once. Store it securely.
    """
    # Generate key
    api_key = _generate_api_key()
    prefix = api_key[:12]  # "sk_live_abc"

    # Hash key for storage
    key_hash = get_password_hash(api_key)

    # Save to database
    key_id = str(uuid4())
    now = datetime.now(timezone.utc)

    new_key = ApiKey(
        id=key_id,
        user_id=current_user.id,
        name=body.name,
        key_hash=key_hash,
        prefix=prefix,
        created_at=now,
    )
    db.add(new_key)

    logger.info("API key created", user_id=current_user.id, key_id=key_id, name=body.name)

    return SuccessResponse(
        success=True,
        data={
            "id": key_id,
            "name": body.name,
            "prefix": prefix,
            "createdAt": now.isoformat(),
            "key": api_key,  # Full key shown only once
            "message": "Save this key securely. It will not be shown again.",
        },
    )


@router.delete("/me/api-keys/{key_id}", response_model=SuccessResponse)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete API key.

    Args:
        key_id: API key ID

    Returns:
        Success message.

    Raises:
        404: API key not found
    """
    # Verify ownership
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="API key not found",
            instance=f"/api/v1/users/me/api-keys/{key_id}",
        )

    # Delete key
    await db.execute(delete(ApiKey).where(ApiKey.id == key_id))

    logger.info("API key deleted", user_id=current_user.id, key_id=key_id)

    return SuccessResponse(
        success=True,
        data={"message": "API key deleted"},
    )


__all__ = ["router"]