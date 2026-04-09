"""FastAPI dependency injection functions.

Provides common dependencies for:
- Database sessions (SQLAlchemy for PostgreSQL)
- Neo4j and Redis connections
- Authentication
- User context

Usage:
    from app.deps import get_db, get_current_user, get_redis

    @router.get("/papers")
    async def list_papers(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        # ...
"""

from typing import AsyncGenerator, Optional

# SQLAlchemy database session (PostgreSQL)
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db as sqlalchemy_get_db

# Neo4j and Redis from core.database
from app.core.database import (
    neo4j_db,
    redis_db,
    get_neo4j,
    get_redis,
)

# Re-export auth dependencies
from app.middleware.auth import (
    oauth2_scheme,
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_roles,
    TokenData,
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
    # Auth
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "require_roles",
    "TokenData",
    # Models
    "User",
]