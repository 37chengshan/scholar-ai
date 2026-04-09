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

from app.config import settings
from app.deps import get_current_user, postgres_db
from app.services.auth_service import User, get_user_by_id, get_user_roles
from app.services.storage_service import get_storage_service
from app.utils.security import get_password_hash, verify_password
from app.utils.problem_detail import ProblemDetail, ErrorTypes, create_error
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/users", tags=["Users"])


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
        existing = await postgres_db.fetchrow(
            "SELECT id FROM users WHERE email = $1 AND id != $2",
            body.email,
            current_user.id,
        )
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
        set_clauses = ", ".join([f'"{k}" = ${i+2}' for i, k in enumerate(updates.keys())])
        query = f'UPDATE users SET {set_clauses}, "updated_at" = $1 WHERE id = ${len(updates) + 2}'
        values = [datetime.now(timezone.utc)] + list(updates.values()) + [current_user.id]
        await postgres_db.execute(query, *values)

    logger.info("Profile updated", user_id=current_user.id, fields=list(updates.keys()))

    # Get updated user
    updated_user = await get_user_by_id(current_user.id)

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
    await postgres_db.execute(
        'UPDATE users SET avatar = $1, "updated_at" = $2 WHERE id = $3',
        storage_key,
        datetime.now(timezone.utc),
        current_user.id,
    )

    logger.info("Avatar uploaded", user_id=current_user.id, storage_key=storage_key)

    return SuccessResponse(
        success=True,
        data={"avatar": avatar_url},
    )


@router.get("/me/settings", response_model=SuccessResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
):
    """Get user settings.

    Returns:
        User settings JSON.
    """
    # Get user with settings
    row = await postgres_db.fetchrow(
        "SELECT settings FROM users WHERE id = $1",
        current_user.id,
    )

    # Default settings if null
    settings_data = row.get("settings") if row else None
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
):
    """Update user settings.

    Args:
        body: Settings update data

    Returns:
        Updated settings.
    """
    # Get current settings
    row = await postgres_db.fetchrow(
        "SELECT settings FROM users WHERE id = $1",
        current_user.id,
    )

    current_settings = row.get("settings") if row else {}
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
    await postgres_db.execute(
        'UPDATE users SET settings = $1, "updated_at" = $2 WHERE id = $3',
        merged,
        datetime.now(timezone.utc),
        current_user.id,
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
    row = await postgres_db.fetchrow(
        "SELECT password_hash FROM users WHERE id = $1",
        current_user.id,
    )

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="User not found",
            instance="/api/v1/users/me/password",
        )

    # Verify current password
    if not verify_password(body.current_password, row["password_hash"]):
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
    await postgres_db.execute(
        'UPDATE users SET password_hash = $1, "updated_at" = $2 WHERE id = $3',
        new_hash,
        datetime.now(timezone.utc),
        current_user.id,
    )

    # Invalidate all refresh tokens (security measure)
    await postgres_db.execute(
        "DELETE FROM refresh_tokens WHERE user_id = $1",
        current_user.id,
    )

    logger.info("Password changed", user_id=current_user.id)

    return SuccessResponse(
        success=True,
        data={"message": "Password changed successfully. Please log in again."},
    )


@router.get("/me/api-keys", response_model=SuccessResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
):
    """List user's API keys.

    Returns:
        List of API keys (without the full key).
    """
    rows = await postgres_db.fetch(
        """SELECT id, name, prefix, created_at, last_used_at
           FROM api_keys
           WHERE user_id = $1
           ORDER BY created_at DESC""",
        current_user.id,
    )

    api_keys = [
        {
            "id": row["id"],
            "name": row["name"],
            "prefix": row.get("prefix"),
            "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
            "lastUsedAt": row["last_used_at"].isoformat() if row.get("last_used_at") else None,
        }
        for row in rows
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

    await postgres_db.execute(
        """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, created_at)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        key_id,
        current_user.id,
        body.name,
        key_hash,
        prefix,
        now,
    )

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
    row = await postgres_db.fetchrow(
        "SELECT id FROM api_keys WHERE id = $1 AND user_id = $2",
        key_id,
        current_user.id,
    )

    if not row:
        raise _create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            detail="API key not found",
            instance=f"/api/v1/users/me/api-keys/{key_id}",
        )

    # Delete key
    await postgres_db.execute(
        "DELETE FROM api_keys WHERE id = $1",
        key_id,
    )

    logger.info("API key deleted", user_id=current_user.id, key_id=key_id)

    return SuccessResponse(
        success=True,
        data={"message": "API key deleted"},
    )


__all__ = ["router"]