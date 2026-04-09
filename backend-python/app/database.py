"""SQLAlchemy 2.0 async database module for ScholarAI.

Provides:
- Async engine configuration with asyncpg driver
- Base class for SQLAlchemy models with AsyncAttrs
- AsyncSessionLocal factory for FastAPI dependency injection
- get_db() async generator for route handlers

Per D-02: SQLAlchemy 2.0 async engine with connection pooling.

Usage:
    from app.database import Base, get_db, AsyncSessionLocal

    # In models
    class User(Base):
        __tablename__ = "users"
        ...

    # In routes
    @router.get("/users")
    async def list_users(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        return result.scalars().all()
"""

from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.utils.logger import logger


# =============================================================================
# SQLAlchemy Base Class
# =============================================================================

class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models.

    AsyncAttrs provides async attribute loading for relationships.
    DeclarativeBase is the SQLAlchemy 2.0 declarative base.
    """
    pass


# =============================================================================
# Async Engine Configuration
# =============================================================================

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True,  # Use SQLAlchemy 2.0 style
    pool_size=20,  # Maximum number of connections to keep in pool
    max_overflow=0,  # Maximum overflow connections (0 = pool_size is hard limit)
    pool_pre_ping=True,  # Check connection health before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Log engine creation
logger.info(
    "SQLAlchemy async engine created",
    pool_size=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)


# =============================================================================
# Async Session Factory
# =============================================================================

# Session factory for creating new sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Required for FastAPI - objects accessible after commit
    autocommit=False,
    autoflush=False,
)

logger.info("AsyncSessionLocal factory created with expire_on_commit=False")


# =============================================================================
# Database Session Dependency
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields an async database session and handles commit/rollback.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session for the request

    The session is automatically:
    - Committed on success
    - Rolled back on exception
    - Closed in finally block
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Database Initialization
# =============================================================================

async def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in models that inherit from Base.
    This is useful for testing and development.

    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_db() -> None:
    """Drop all database tables.

    Used for testing cleanup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")


# =============================================================================
# Connection Event Handlers
# =============================================================================

@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new database connections."""
    logger.debug("New database connection established")


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection return to pool."""
    logger.debug("Connection returned to pool")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "drop_db",
]