"""Import domain rate limiter - separate from search domain.

Per D-07:
- Semantic Scholar: 1 request/sec + exponential backoff
- arXiv: 3 second interval + result caching

This module is isolated from search/shared.py to avoid cross-domain coupling.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import redis.asyncio as redis

from app.config import settings
from app.utils.logger import logger


@dataclass
class ImportRateLimiter:
    """Token bucket rate limiter with exponential backoff for import operations.

    Implements:
    - Token bucket algorithm for rate limiting
    - Exponential backoff on consecutive failures
    - Async lock for thread safety

    Note: Uses field(default_factory) for mutable defaults per Python best practices.
    """

    min_interval: float
    max_backoff: float = 60.0
    consecutive_failures: int = 0
    last_request_time: float = field(default_factory=lambda: 0.0)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> None:
        """Wait before next request, with exponential backoff on failures.

        Calculates wait time based on:
        1. Minimum interval between requests
        2. Exponential backoff for consecutive failures
        """
        async with self._lock:
            now = time.time()

            # Calculate backoff for failures
            if self.consecutive_failures > 0:
                # Exponential backoff: 1s, 2s, 4s, 8s, ...
                backoff = min((2 ** self.consecutive_failures) * 1.0, self.max_backoff)
            else:
                backoff = 0.0

            # Calculate wait time
            elapsed = now - self.last_request_time
            wait_time = max(self.min_interval - elapsed + backoff, 0)

            if wait_time > 0:
                logger.debug(
                    "Import rate limiter waiting",
                    wait_seconds=wait_time,
                    consecutive_failures=self.consecutive_failures,
                    min_interval=self.min_interval,
                )
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def record_success(self) -> None:
        """Reset failure counter on successful request."""
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Increment failure counter for exponential backoff."""
        self.consecutive_failures += 1
        logger.warning(
            "Import rate limiter recorded failure",
            consecutive_failures=self.consecutive_failures,
            min_interval=self.min_interval,
        )


# Singleton rate limiters for import domain (NOT shared with search)
_arxiv_import_limiter: Optional[ImportRateLimiter] = None
_s2_import_limiter: Optional[ImportRateLimiter] = None
_unpaywall_import_limiter: Optional[ImportRateLimiter] = None
_openalex_import_limiter: Optional[ImportRateLimiter] = None


def get_arxiv_import_limiter() -> ImportRateLimiter:
    """Get or create arXiv import rate limiter (3s interval).

    Per gpt意见.md Section 4.1: arXiv API recommends 3 second delay for consecutive requests.
    """
    global _arxiv_import_limiter
    if _arxiv_import_limiter is None:
        _arxiv_import_limiter = ImportRateLimiter(min_interval=3.0)
    return _arxiv_import_limiter


def get_s2_import_limiter() -> ImportRateLimiter:
    """Get or create S2 import rate limiter (1rps).

    Per gpt意见.md Section 4.2: Semantic Scholar personal API key gets 1 request/sec quota.
    """
    global _s2_import_limiter
    if _s2_import_limiter is None:
        _s2_import_limiter = ImportRateLimiter(min_interval=1.0)
    return _s2_import_limiter


def get_unpaywall_import_limiter() -> ImportRateLimiter:
    """Get or create Unpaywall import rate limiter (2rps conservative)."""
    global _unpaywall_import_limiter
    if _unpaywall_import_limiter is None:
        _unpaywall_import_limiter = ImportRateLimiter(min_interval=0.5)
    return _unpaywall_import_limiter


def get_openalex_import_limiter() -> ImportRateLimiter:
    """Get or create OpenAlex import rate limiter (2rps conservative)."""
    global _openalex_import_limiter
    if _openalex_import_limiter is None:
        _openalex_import_limiter = ImportRateLimiter(min_interval=0.5)
    return _openalex_import_limiter


class ImportCache:
    """Redis cache for import resolution results.

    Per D-07: Cache arXiv queries for 1 day (86400s).
    Per D-10: Cache S2 paper details for 7 days (604800s).
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get cached value by key."""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning("Import cache get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl_seconds: int = 86400) -> None:
        """Cache value with TTL (default 1 day for arXiv queries)."""
        try:
            await self.redis.setex(key, ttl_seconds, value)
            logger.debug("Import cache set", key=key, ttl=ttl_seconds)
        except Exception as e:
            logger.warning("Import cache set failed", key=key, error=str(e))

    def make_arxiv_cache_key(self, query: str) -> str:
        """Generate cache key for arXiv resolution."""
        return f"import:arxiv:resolve:{query}"

    def make_s2_cache_key(self, paper_id: str) -> str:
        """Generate cache key for S2 paper details."""
        return f"import:s2:details:{paper_id}"

    def make_doi_cache_key(self, doi: str) -> str:
        """Generate cache key for DOI resolution."""
        return f"import:doi:resolve:{doi}"


# Singleton cache instance
_import_cache: Optional[ImportCache] = None


async def get_import_cache() -> ImportCache:
    """Get or create ImportCache with Redis client."""
    global _import_cache
    if _import_cache is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
        _import_cache = ImportCache(redis_client)
    return _import_cache


__all__ = [
    "ImportRateLimiter",
    "ImportCache",
    "get_arxiv_import_limiter",
    "get_s2_import_limiter",
    "get_unpaywall_import_limiter",
    "get_openalex_import_limiter",
    "get_import_cache",
]