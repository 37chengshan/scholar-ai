"""Redis client configuration for ScholarAI.

Redis database allocation:
- DB 0: JWT blacklist, sessions (existing usage from Phase 06)
- DB 1: Celery broker (Phase 11)
- DB 2: Celery backend (Phase 11)
"""

import redis.asyncio as aioredis
from typing import Optional

# Redis URLs for different purposes
REDIS_BASE_URL = 'redis://localhost:6379'

# Celery broker/backend URLs (sync Redis - Celery requirement)
CELERY_BROKER_URL = f'{REDIS_BASE_URL}/1'
CELERY_BACKEND_URL = f'{REDIS_BASE_URL}/2'

# Async Redis client for application logic (DB 0)
async_redis: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Get or create async Redis client for application logic."""
    global async_redis

    if async_redis is None:
        async_redis = aioredis.from_url(
            f'{REDIS_BASE_URL}/0',
            encoding='utf-8',
            decode_responses=True
        )

    return async_redis


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global async_redis

    if async_redis:
        await async_redis.close()
        async_redis = None


__all__ = [
    'CELERY_BROKER_URL',
    'CELERY_BACKEND_URL',
    'get_redis_client',
    'close_redis_client',
]