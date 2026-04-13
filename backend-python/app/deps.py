"""FastAPI dependency injection functions.

Provides common dependencies for:
- Database sessions (SQLAlchemy for PostgreSQL)
- Neo4j and Redis connections
- Authentication
- User context

Architecture Decision D-04:
    - Unified CurrentUser dependency for all protected routes
    - Returns User object with id, email, roles

Usage:
    from app.deps import get_db, CurrentUser

    @router.get("/papers")
    async def list_papers(
        db: AsyncSession = Depends(get_db),
        user: User = CurrentUser,
    ):
        # user.id, user.email, user.roles available
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends

# SQLAlchemy database session (PostgreSQL)
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db as sqlalchemy_get_db, AsyncSessionLocal

# Neo4j and Redis from core.database
from app.core.database import (
    neo4j_db,
    redis_db,
    get_neo4j,
    get_redis,
)

# Re-export auth dependencies from unified source (middleware/auth.py)
# AUTH-01: Single auth source with blacklist check for all APIs
from app.middleware.auth import (
    oauth2_scheme,
    get_current_user,
    get_current_user_id,
    get_current_active_user,
    get_optional_user,
    require_roles,
    TokenData,
    CurrentUser,
    CurrentUserId,
)

# Re-export user model
from app.services.auth_service import User


# Re-export SQLAlchemy get_db directly (it's already a proper async generator)
get_db = sqlalchemy_get_db


__all__ = [
    # Database (SQLAlchemy)
    "get_db",
    # Neo4j and Redis
    "get_neo4j",
    "get_redis",
    "neo4j_db",
    "redis_db",
    # Auth (unified from middleware/auth.py)
    "CurrentUser",
    "CurrentUserId",
    "oauth2_scheme",
    "get_current_user",
    "get_current_user_id",
    "get_current_active_user",
    "get_optional_user",
    "require_roles",
    "TokenData",
    # Models
    "User",
]
