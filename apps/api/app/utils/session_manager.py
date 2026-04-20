"""Session management with PostgreSQL + Redis synchronization.

Provides Session lifecycle management:
- Create sessions with 30-day expiration
- Retrieve sessions (Redis cache -> PostgreSQL fallback)
- Update sessions with dual storage sync
- Delete sessions from both stores
- Cleanup expired sessions

Redis cache structure:
- session:{session_id} -> {id, title, messages (recent 20), context}
- user:{user_id}:active_sessions -> [session_id1, session_id2, ...]
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import uuid

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import redis_db
from app.database import AsyncSessionLocal
from app.models.orm_session import Session
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse
from app.services.message_service import message_service
from app.utils.logger import logger

# Redis cache TTL
SESSION_CACHE_TTL = 7 * 24 * 3600  # 7 days
USER_SESSIONS_TTL = 30 * 24 * 3600  # 30 days

# Session expiration period
SESSION_EXPIRATION_DAYS = 30

# Maximum messages to cache in Redis
MAX_CACHED_MESSAGES = 20


class SessionManager:
    """Manages Session lifecycle with PostgreSQL + Redis synchronization."""

    def __init__(self):
        """Initialize SessionManager with database clients."""
        self.redis = redis_db

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> SessionResponse:
        """
        Create a new session with 30-day expiration.

        Args:
            user_id: User UUID who owns the session
            title: Optional session title

        Returns:
            Created session with all fields
        """
        try:
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires_at = now + timedelta(days=SESSION_EXPIRATION_DAYS)

            async with AsyncSessionLocal() as db:
                # Create Session ORM object
                session_obj = Session(
                    id=session_id,
                    user_id=user_id,
                    title=title,
                    status="active",
                    session_metadata={},
                    message_count=0,
                    tool_call_count=0,
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                    expires_at=expires_at
                )

                db.add(session_obj)
                await db.commit()
                await db.refresh(session_obj)

            # Sync to Redis cache
            await self._sync_to_redis(session_obj)

            # Add to user's active sessions index
            await self._add_to_user_sessions(user_id, session_id)

            logger.info(f"Created session {session_id} for user {user_id}")

            return self._orm_to_response(session_obj)

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """
        Retrieve session by ID (Redis cache -> PostgreSQL fallback).

        Args:
            session_id: Session UUID

        Returns:
            Session if found, None otherwise
        """
        try:
            # Try Redis cache first
            cached = await self._get_from_redis(session_id)
            if cached:
                logger.debug(f"Session {session_id} cache hit")
                return SessionResponse.model_validate(cached)

            # Fallback to PostgreSQL with SQLAlchemy
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session_obj = result.scalar_one_or_none()

                if not session_obj:
                    logger.debug(f"Session {session_id} not found")
                    return None

                # Sync to Redis cache for future requests
                await self._sync_to_redis(session_obj)

                logger.debug(f"Session {session_id} retrieved from database")
                return self._orm_to_response(session_obj)

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    async def update_session(
        self,
        session_id: str,
        updates: SessionUpdate
    ) -> Optional[SessionResponse]:
        """
        Update session fields and sync to both stores.

        Args:
            session_id: Session UUID
            updates: Fields to update (partial)

        Returns:
            Updated session if found, None otherwise
        """
        try:
            now = datetime.utcnow()

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session_obj = result.scalar_one_or_none()

                if not session_obj:
                    logger.warning(f"Session {session_id} not found for update")
                    return None

                # Apply updates from SessionUpdate
                update_data = updates.model_dump(exclude_unset=True)

                for field, value in update_data.items():
                    if field == "metadata":
                        setattr(session_obj, "session_metadata", value)
                    else:
                        setattr(session_obj, field, value)

                # Always update timestamps
                session_obj.updated_at = now
                session_obj.last_activity_at = now

                await db.commit()
                await db.refresh(session_obj)

            # Sync to Redis cache
            await self._sync_to_redis(session_obj)

            logger.info(f"Updated session {session_id}")
            return self._orm_to_response(session_obj)

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from both PostgreSQL and Redis.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            async with AsyncSessionLocal() as db:
                # Get session to find user_id
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session_obj = result.scalar_one_or_none()

                if not session_obj:
                    logger.warning(f"Session {session_id} not found for deletion")
                    return False

                user_id = session_obj.user_id

                # Delete dependent chat messages first so PostgreSQL FK checks do not fail.
                await message_service.delete_session_messages(session_id)

                # Delete session from PostgreSQL.
                await db.execute(
                    delete(Session).where(Session.id == session_id)
                )
                await db.commit()

            # Delete from Redis cache
            await self._delete_from_redis(session_id)

            # Remove from user's active sessions
            await self._remove_from_user_sessions(user_id, session_id)

            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        status: str = "active"
    ) -> List[SessionResponse]:
        """
        List user's sessions with optional filtering.

        Args:
            user_id: User UUID
            limit: Maximum number of sessions to return
            status: Filter by status (active, archived, deleted)

        Returns:
            List of sessions ordered by last activity
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session)
                    .where(and_(Session.user_id == user_id, Session.status == status))
                    .order_by(Session.last_activity_at.desc())
                    .limit(limit)
                )
                sessions = result.scalars().all()

            logger.debug(f"Found {len(sessions)} sessions for user {user_id}")
            return [self._orm_to_response(s) for s in sessions]

        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            raise

    async def cleanup_expired_sessions(self) -> int:
        """
        Delete sessions older than 30 days.

        Returns:
            Number of sessions deleted
        """
        try:
            now = datetime.utcnow()

            async with AsyncSessionLocal() as db:
                # Find expired sessions
                result = await db.execute(
                    select(Session).where(Session.expires_at < now)
                )
                expired_sessions = result.scalars().all()

                deleted_count = 0
                for session_obj in expired_sessions:
                    await self.delete_session(session_obj.id)
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} expired sessions")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise

    # Private helper methods

    def _orm_to_response(self, session_obj: Session) -> SessionResponse:
        """Convert SQLAlchemy Session ORM object to SessionResponse."""
        return SessionResponse(
            id=str(session_obj.id),
            user_id=str(session_obj.user_id),
            title=session_obj.title,
            status=session_obj.status,
            metadata=session_obj.session_metadata,
            message_count=session_obj.message_count,
            tool_call_count=session_obj.tool_call_count,
            created_at=session_obj.created_at,
            updated_at=session_obj.updated_at,
            last_activity_at=session_obj.last_activity_at,
            expires_at=session_obj.expires_at,
        )

    async def _sync_to_redis(self, session_obj: Session) -> None:
        """Sync session data to Redis cache."""
        try:
            cache_key = f"session:{session_obj.id}"

            # Prepare session data
            session_data = {
                "id": str(session_obj.id),
                "user_id": str(session_obj.user_id),
                "title": session_obj.title,
                "status": session_obj.status,
                "metadata": session_obj.session_metadata,
                "message_count": session_obj.message_count,
                "tool_call_count": session_obj.tool_call_count,
                "created_at": session_obj.created_at.isoformat(),
                "updated_at": session_obj.updated_at.isoformat(),
                "last_activity_at": session_obj.last_activity_at.isoformat(),
                "expires_at": session_obj.expires_at.isoformat() if session_obj.expires_at else None,
            }

            # Save to Redis with TTL using the underlying client
            if self.redis.client:
                await self.redis.client.setex(
                    cache_key,
                    SESSION_CACHE_TTL,
                    json.dumps(session_data)
                )

            logger.debug(f"Synced session {session_obj.id} to Redis")

        except Exception as e:
            logger.error(f"Failed to sync session to Redis: {e}")
            # Don't raise - cache failure shouldn't block operations

    async def _get_from_redis(self, session_id: str) -> Optional[Dict]:
        """Retrieve session from Redis cache."""
        try:
            cache_key = f"session:{session_id}"

            cached_data = await self.redis.get(cache_key)

            if cached_data:
                return json.loads(cached_data)
            return None

        except Exception as e:
            logger.error(f"Failed to get session from Redis: {e}")
            return None

    async def _delete_from_redis(self, session_id: str) -> None:
        """Delete session from Redis cache."""
        try:
            cache_key = f"session:{session_id}"
            await self.redis.delete(cache_key)
            logger.debug(f"Deleted session {session_id} from Redis")

        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")

    async def _add_to_user_sessions(self, user_id: str, session_id: str) -> None:
        """Add session to user's active sessions index."""
        try:
            key = f"user:{user_id}:active_sessions"
            if self.redis.client:
                await self.redis.client.sadd(key, session_id)
                await self.redis.client.expire(key, USER_SESSIONS_TTL)
            logger.debug(f"Added session {session_id} to user {user_id} active sessions")

        except Exception as e:
            logger.error(f"Failed to add to user sessions: {e}")

    async def _remove_from_user_sessions(self, user_id: str, session_id: str) -> None:
        """Remove session from user's active sessions index."""
        try:
            key = f"user:{user_id}:active_sessions"
            if self.redis.client:
                await self.redis.client.srem(key, session_id)
            logger.debug(f"Removed session {session_id} from user {user_id} active sessions")

        except Exception as e:
            logger.error(f"Failed to remove from user sessions: {e}")


# Singleton instance
session_manager = SessionManager()
