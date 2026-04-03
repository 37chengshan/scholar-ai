"""Concurrent control for external paper additions.

Provides:
- ConcurrentControl: Limit simultaneous external paper additions per user
- Redis-based counter with TTL
- Integration hooks for paper addition workflow

Requirements:
- API-02: External search routes
"""

from typing import Optional
import redis.asyncio as redis

from app.core.config import settings
from app.utils.logger import logger


class ConcurrentControl:
    """Manage concurrent external paper additions per user.

    Uses Redis counter to track pending papers per user.
    Limits concurrent additions to prevent system overload.

    Attributes:
        MAX_CONCURRENT: Maximum simultaneous pending papers (5)
        TTL: Counter expiration time in seconds (3600 = 1 hour)
    """

    MAX_CONCURRENT = 5
    TTL = 3600  # 1 hour

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize ConcurrentControl.

        Args:
            redis_client: Optional Redis client (creates own if not provided)
        """
        self._redis = redis_client
        self._owns_redis = redis_client is None

    async def _get_redis(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self._redis

    async def can_add_paper(self, user_id: str) -> bool:
        """Check if user can add another paper.

        Args:
            user_id: User identifier

        Returns:
            True if user has < MAX_CONCURRENT pending papers

        Example:
            >>> control = ConcurrentControl()
            >>> await control.can_add_paper("user-123")
            True  # If user has 0-4 pending papers
        """
        redis_client = await self._get_redis()
        key = f"user:{user_id}:pending_papers"

        try:
            count = await redis_client.get(key)
            current = int(count) if count else 0

            logger.debug(
                "Concurrent limit check",
                user_id=user_id,
                current_count=current,
                max_allowed=self.MAX_CONCURRENT,
            )

            return current < self.MAX_CONCURRENT

        except Exception as e:
            logger.error("Failed to check concurrent limit", user_id=user_id, error=str(e))
            # Fail open: allow addition if Redis check fails
            return True

    async def increment_pending(self, user_id: str) -> int:
        """Increment pending paper counter for user.

        Args:
            user_id: User identifier

        Returns:
            New counter value after increment

        Raises:
            ValueError: If increment would exceed MAX_CONCURRENT

        Example:
            >>> control = ConcurrentControl()
            >>> await control.increment_pending("user-123")
            1  # Counter now at 1
        """
        redis_client = await self._get_redis()
        key = f"user:{user_id}:pending_papers"

        # Check limit first
        if not await self.can_add_paper(user_id):
            logger.warning(
                "Concurrent limit exceeded",
                user_id=user_id,
                max_allowed=self.MAX_CONCURRENT,
            )
            raise ValueError(f"User {user_id} has reached concurrent limit of {self.MAX_CONCURRENT}")

        try:
            # INCR is atomic, returns new value
            new_count = await redis_client.incr(key)
            await redis_client.expire(key, self.TTL)

            logger.info(
                "Incremented pending papers",
                user_id=user_id,
                new_count=new_count,
                ttl=self.TTL,
            )

            return new_count

        except Exception as e:
            logger.error("Failed to increment pending counter", user_id=user_id, error=str(e))
            raise

    async def decrement_pending(self, user_id: str) -> int:
        """Decrement pending paper counter for user.

        Called when paper processing completes or fails.

        Args:
            user_id: User identifier

        Returns:
            New counter value after decrement

        Example:
            >>> control = ConcurrentControl()
            >>> await control.decrement_pending("user-123")
            0  # Counter now at 0
        """
        redis_client = await self._get_redis()
        key = f"user:{user_id}:pending_papers"

        try:
            # DECR is atomic, returns new value
            new_count = await redis_client.decr(key)

            # Delete key if counter reaches 0
            if new_count <= 0:
                await redis_client.delete(key)
                logger.info("Deleted pending counter", user_id=user_id)
                return 0

            logger.info(
                "Decremented pending papers",
                user_id=user_id,
                new_count=new_count,
            )

            return new_count

        except Exception as e:
            logger.error("Failed to decrement pending counter", user_id=user_id, error=str(e))
            raise

    async def get_pending_count(self, user_id: str) -> int:
        """Get current pending paper count for user.

        Args:
            user_id: User identifier

        Returns:
            Current number of pending papers (0 if no key exists)
        """
        redis_client = await self._get_redis()
        key = f"user:{user_id}:pending_papers"

        try:
            count = await redis_client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error("Failed to get pending count", user_id=user_id, error=str(e))
            return 0

    async def close(self):
        """Close Redis connection if owned by this instance."""
        if self._owns_redis and self._redis:
            await self._redis.close()
            self._redis = None


# Singleton instance for dependency injection
_concurrent_control: Optional[ConcurrentControl] = None


def get_concurrent_control() -> ConcurrentControl:
    """Get singleton ConcurrentControl instance."""
    global _concurrent_control
    if _concurrent_control is None:
        _concurrent_control = ConcurrentControl()
    return _concurrent_control