"""FastAPI dependency injection functions.

Provides common dependencies for:
- Database sessions
- Authentication
- User context

Usage:
    from app.deps import get_db, get_current_user, get_redis

    @router.get("/papers")
    async def list_papers(
        db = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        # ...
"""

from typing import AsyncGenerator, Optional

# Re-export database dependencies
from app.core.database import (
    postgres_db,
    neo4j_db,
    redis_db,
    get_postgres,
    get_neo4j,
    get_redis,
    get_db_connection,
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


async def get_db():
    """Get PostgreSQL database instance.

    This is the primary database dependency.
    Use for direct SQL queries via postgres_db.

    Returns:
        PostgresDB instance

    Example:
        @router.get("/items")
        async def get_items(db = Depends(get_db)):
            rows = await db.fetch("SELECT * FROM items")
            return rows
    """
    return postgres_db


__all__ = [
    # Database
    "get_db",
    "get_postgres",
    "get_neo4j",
    "get_redis",
    "get_db_connection",
    "postgres_db",
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