"""Authentication dependencies for Python FastAPI endpoints.

Provides user authentication via X-User-ID header pass-through.

Architecture Decision D-01:
    - OAuth 2.0 authentication handled directly in Python backend (Phase 27)
    - User context extracted from JWT cookies or Authorization header
    - User ID available via CurrentUserId dependency

Usage for user endpoints:
    from app.core.auth import CurrentUserId

    @router.get("/protected")
    async def protected_endpoint(user_id: str = CurrentUserId):
        # user_id is guaranteed to be authenticated
        return {"user_id": user_id}
"""

from fastapi import Depends

from app.utils.user_context import get_current_user_id, require_user_id


# =============================================================================
# User Authentication Dependencies (from X-User-ID header)
# =============================================================================

# Convenience dependency for user endpoints
# Usage: async def endpoint(user_id: str = CurrentUserId):
CurrentUserId = Depends(get_current_user_id)

# Alias for backwards compatibility
RequireUserId = Depends(require_user_id)


__all__ = [
    "get_current_user_id",
    "require_user_id",
    "CurrentUserId",
    "RequireUserId",
]
