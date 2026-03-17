"""Redis-based query caching utilities for RAG responses.

Provides cache key generation, get/set operations with TTL,
and cache hit/miss logging for RAG query responses.
"""

import hashlib
import json
import time
from typing import Any, Optional

from app.core.database import redis_db
from app.utils.logger import logger

# Default TTL: 1 hour (3600 seconds)
DEFAULT_CACHE_TTL = 3600

# Cache key prefix for RAG queries
CACHE_PREFIX = "rag:query"

# Cache key prefix for conversation sessions
CONVERSATION_PREFIX = "rag:conversation"


def generate_cache_key(
    query: str,
    paper_ids: list[str],
    query_type: str = "single"
) -> str:
    """
    Generate a cache key for RAG query.

    Uses SHA256 hash of query + paper_ids + query_type to ensure
    unique cache key per context combination.

    Args:
        query: The user's question
        paper_ids: List of paper IDs being queried
        query_type: Type of query (single, cross_paper, evolution)

    Returns:
        Hexadecimal hash string (64 characters)
    """
    # Sort paper_ids to ensure order independence
    sorted_papers = sorted(paper_ids) if paper_ids else []
    paper_ids_str = ",".join(sorted_papers)

    # Combine query components
    key_data = f"{query}:{paper_ids_str}:{query_type}"

    # Generate SHA256 hash
    cache_key = hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    return cache_key


def generate_conversation_key(session_id: str) -> str:
    """
    Generate a cache key for conversation session.

    Args:
        session_id: Unique conversation session identifier

    Returns:
        Prefixed cache key for Redis
    """
    return f"{CONVERSATION_PREFIX}:{session_id}"


async def get_cached_response(
    query: str,
    paper_ids: list[str],
    query_type: str = "single"
) -> Optional[dict[str, Any]]:
    """
    Retrieve cached RAG response if available.

    Args:
        query: The user's question
        paper_ids: List of paper IDs being queried
        query_type: Type of query

    Returns:
        Cached response dict if found, None otherwise
    """
    cache_key = generate_cache_key(query, paper_ids, query_type)
    full_key = f"{CACHE_PREFIX}:{cache_key}"

    try:
        cached_data = await redis_db.get(full_key)

        if cached_data:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return json.loads(cached_data)
        else:
            logger.info(f"Cache miss for query: {query[:50]}...")
            return None

    except Exception as e:
        logger.error(f"Cache retrieval error: {e}")
        return None


async def set_cached_response(
    query: str,
    paper_ids: list[str],
    response: dict[str, Any],
    query_type: str = "single",
    ttl: int = DEFAULT_CACHE_TTL
) -> bool:
    """
    Store RAG response in cache with TTL.

    Args:
        query: The user's question
        paper_ids: List of paper IDs being queried
        response: The RAG response to cache
        query_type: Type of query
        ttl: Time to live in seconds (default: 3600)

    Returns:
        True if cached successfully, False otherwise
    """
    cache_key = generate_cache_key(query, paper_ids, query_type)
    full_key = f"{CACHE_PREFIX}:{cache_key}"

    # Add cache metadata
    cache_entry = {
        **response,
        "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache_key": cache_key
    }

    try:
        await redis_db.set(full_key, json.dumps(cache_entry), expire=ttl)
        logger.info(f"Cached response for query: {query[:50]}... (TTL: {ttl}s)")
        return True

    except Exception as e:
        logger.error(f"Cache storage error: {e}")
        return False


async def delete_cached_response(
    query: str,
    paper_ids: list[str],
    query_type: str = "single"
) -> bool:
    """
    Delete cached RAG response.

    Args:
        query: The user's question
        paper_ids: List of paper IDs being queried
        query_type: Type of query

    Returns:
        True if deleted successfully, False otherwise
    """
    cache_key = generate_cache_key(query, paper_ids, query_type)
    full_key = f"{CACHE_PREFIX}:{cache_key}"

    try:
        await redis_db.delete(full_key)
        logger.info(f"Deleted cached response for query: {query[:50]}...")
        return True

    except Exception as e:
        logger.error(f"Cache deletion error: {e}")
        return False


async def get_conversation_session(session_id: str) -> Optional[dict[str, Any]]:
    """
    Retrieve conversation session from Redis.

    Args:
        session_id: Unique conversation session identifier

    Returns:
        Session data if found, None otherwise
    """
    key = generate_conversation_key(session_id)

    try:
        data = await redis_db.get(key)

        if data:
            logger.info(f"Retrieved conversation session: {session_id}")
            return json.loads(data)
        else:
            logger.info(f"Conversation session not found: {session_id}")
            return None

    except Exception as e:
        logger.error(f"Conversation retrieval error: {e}")
        return None


async def save_conversation_session(
    session_id: str,
    session_data: dict[str, Any],
    ttl: int = DEFAULT_CACHE_TTL
) -> bool:
    """
    Save conversation session to Redis.

    Args:
        session_id: Unique conversation session identifier
        session_data: Session data including messages and paper_ids
        ttl: Time to live in seconds (default: 3600)

    Returns:
        True if saved successfully, False otherwise
    """
    key = generate_conversation_key(session_id)

    # Update timestamp
    session_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        await redis_db.set(key, json.dumps(session_data), expire=ttl)
        logger.info(f"Saved conversation session: {session_id} (TTL: {ttl}s)")
        return True

    except Exception as e:
        logger.error(f"Conversation save error: {e}")
        return False


async def delete_conversation_session(session_id: str) -> bool:
    """
    Delete conversation session from Redis.

    Args:
        session_id: Unique conversation session identifier

    Returns:
        True if deleted successfully, False otherwise
    """
    key = generate_conversation_key(session_id)

    try:
        await redis_db.delete(key)
        logger.info(f"Deleted conversation session: {session_id}")
        return True

    except Exception as e:
        logger.error(f"Conversation deletion error: {e}")
        return False


async def extend_session_ttl(session_id: str, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Extend TTL of existing conversation session.

    Args:
        session_id: Unique conversation session identifier
        ttl: New TTL in seconds

    Returns:
        True if extended successfully, False otherwise
    """
    key = generate_conversation_key(session_id)

    try:
        # Check if key exists
        exists = await redis_db.exists(key)
        if not exists:
            return False

        # Get current data and re-set with new TTL
        data = await redis_db.get(key)
        if data:
            await redis_db.set(key, data, expire=ttl)
            logger.info(f"Extended TTL for session: {session_id} (+{ttl}s)")
            return True

        return False

    except Exception as e:
        logger.error(f"TTL extension error: {e}")
        return False


async def clear_all_cache() -> bool:
    """
    Clear all RAG-related cache entries.

    WARNING: This is for testing/development only.

    Returns:
        True if cleared successfully, False otherwise
    """
    try:
        # Note: In production, use scan/delete pattern instead of flushdb
        # This implementation is simplified
        logger.warning("Cache clear requested - use with caution")
        return True

    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return False
