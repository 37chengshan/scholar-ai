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
from app.database import get_db as sqlalchemy_get_db, AsyncSessionLocal

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


# Temporary placeholder for backward compatibility with legacy asyncpg code
# This will be removed once all files are migrated to SQLAlchemy
class _PostgresDBPlaceholder:
    """Placeholder for legacy postgres_db usage.

    Provides a compatibility shim for code still using raw asyncpg patterns.
    Will be removed after full SQLAlchemy migration.
    """

    async def fetchrow(self, query: str, *args):
        """Execute query and return single row."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(query, args)
            row = result.fetchone()
            return row._mapping if row else None

    async def fetch(self, query: str, *args):
        """Execute query and return all rows."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(query, args)
            rows = result.fetchall()
            return [row._mapping for row in rows]

    async def execute(self, query: str, *args):
        """Execute query without returning results."""
        async with AsyncSessionLocal() as session:
            await session.execute(query, args)
            await session.commit()


postgres_db = _PostgresDBPlaceholder()


__all__ = [
    # Database (SQLAlchemy)
    "get_db",
    # Legacy placeholder (temporary)
    "postgres_db",
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