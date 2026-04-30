"""Semantic similarity-based cache for RAG queries.

Provides cache lookup using vector similarity instead of exact key matching.
This allows semantically similar queries to return cached responses,
reducing redundant LLM API calls.

User decision D-02: threshold=0.95, TTL=24 hours (86400 seconds).
"""

import hashlib
import json
import time
import numpy as np
from typing import Any, Dict, List, Optional

from app.core.embedding.factory import get_embedding_service
from app.core.database import redis_db
from app.utils.logger import logger


class SemanticCache:
    """Redis-backed semantic cache for RAG queries.

    Uses embedding similarity to match queries, allowing paraphrased
    questions to benefit from cached responses.

    Attributes:
        threshold: Minimum cosine similarity for cache hit (default: 0.95)
        ttl: Time to live in seconds (default: 86400 = 24 hours)
        embedding_service: Service for generating query embeddings
        prefix: Redis key prefix for semantic cache entries
    """

    def __init__(
        self,
        threshold: float = 0.95,
        ttl: int = 86400,
        max_entries: int = 1000,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize SemanticCache.

        Args:
            threshold: Minimum similarity threshold for cache hit (default: 0.95)
            ttl: Cache entry TTL in seconds (default: 86400 for 24 hours)
            max_entries: Maximum number of cache entries before eviction
            embedding_service: Optional embedding service instance (defaults to unified embedding factory)
        """
        self.threshold = threshold
        self.ttl = ttl
        self.max_entries = max_entries
        self.embedding_service = embedding_service or get_embedding_service()
        self.prefix = "rag:semantic_cache"

    async def _enforce_cache_limit(self) -> None:
        """Evict oldest entries when cache size exceeds limit."""
        pattern = f"{self.prefix}:*"
        entries: List[tuple[str, float]] = []
        try:
            async for key in redis_db.client.scan_iter(match=pattern):
                cached_data = await redis_db.get(key)
                if not cached_data:
                    continue
                try:
                    cached = json.loads(cached_data)
                    entries.append((key, float(cached.get("timestamp", 0.0))))
                except Exception:
                    entries.append((key, 0.0))

            if len(entries) <= self.max_entries:
                return

            entries.sort(key=lambda item: item[1])
            overflow = len(entries) - self.max_entries
            for key, _ in entries[:overflow]:
                await redis_db.delete(key)

            logger.info(
                "Semantic cache eviction completed",
                removed=overflow,
                max_entries=self.max_entries,
            )
        except Exception as e:
            logger.warning(f"Semantic cache eviction failed: {e}")

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Cosine similarity value between -1.0 and 1.0
        """
        a_np = np.array(a)
        b_np = np.array(b)

        dot_product = np.dot(a_np, b_np)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    async def get(
        self,
        query: str,
        paper_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if semantically similar query exists.

        Scans Redis for cache entries matching the paper_ids, then compares
        query embeddings using cosine similarity.

        Args:
            query: User question to look up
            paper_ids: List of paper IDs in the query context

        Returns:
            Cached response dict if similarity >= threshold, None otherwise
        """
        if not query or not paper_ids:
            return None

        # Generate embedding for incoming query
        query_embedding = self.embedding_service.encode_text(query)

        # Build key pattern for matching paper_ids
        paper_key = ':'.join(sorted(paper_ids))
        pattern = f"{self.prefix}:*:{paper_key}"

        # Scan for matching keys (use Redis SCAN, not KEYS for production)
        keys = []
        try:
            async for key in redis_db.client.scan_iter(match=pattern):
                keys.append(key)
        except Exception as e:
            logger.warning(f"Redis scan failed: {e}")
            return None

        if not keys:
            logger.debug(f"No cached queries for paper_ids: {paper_ids}")
            return None

        # Compare similarity with each cached query
        best_similarity = 0.0
        best_response = None

        for key in keys:
            try:
                cached_data = await redis_db.get(key)
                if not cached_data:
                    continue

                cached = json.loads(cached_data)
                cached_embedding = cached.get("embedding", [])

                if not cached_embedding or len(cached_embedding) == 0:
                    continue

                # Calculate similarity
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                logger.debug(
                    f"Similarity check: {similarity:.3f} vs threshold {self.threshold} "
                    f"for cached query '{cached.get('query', '')[:30]}...'"
                )

                if similarity >= self.threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_response = cached.get("response")

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid cached data at key {key}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing cached entry {key}: {e}")
                continue

        if best_response:
            logger.info(
                f"Semantic cache hit: similarity={best_similarity:.3f} "
                f"for query '{query[:50]}...'"
            )
            return best_response

        logger.info(
            f"Semantic cache miss: best_similarity={best_similarity:.3f} < {self.threshold} "
            f"for query '{query[:50]}...'"
        )
        return None

    async def set(
        self,
        query: str,
        paper_ids: List[str],
        response: Dict[str, Any],
        query_type: str = "single",
    ) -> bool:
        """Cache RAG response with query embedding.

        Stores the query, its embedding, and the response in Redis
        with the specified TTL.

        Args:
            query: User question to cache
            paper_ids: List of paper IDs in the query context
            response: RAG response to cache
            query_type: Type of query (single, cross_paper, evolution)

        Returns:
            True if cached successfully, False otherwise
        """
        if not query:
            logger.warning("Cannot cache empty query")
            return False

        # Generate embedding for query
        query_embedding = self.embedding_service.encode_text(query)

        # Build cache key
        paper_key = ':'.join(sorted(paper_ids)) if paper_ids else "all"
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        cache_key = f"{self.prefix}:{query_hash}:{paper_key}"

        # Prepare cache data
        cache_data = {
            "query": query,
            "embedding": query_embedding,
            "response": response,
            "paper_ids": paper_ids,
            "query_type": query_type,
            "timestamp": time.time(),
        }

        try:
            await redis_db.set(cache_key, json.dumps(cache_data), expire=self.ttl)
            await self._enforce_cache_limit()
            logger.info(
                f"Cached semantic response for query '{query[:50]}...' "
                f"(key: {cache_key}, TTL: {self.ttl}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
            return False

    async def clear(
        self,
        paper_ids: Optional[List[str]] = None,
    ) -> int:
        """Clear semantic cache entries.

        Args:
            paper_ids: Optional list of paper IDs to clear specific entries.
                      If None, clears all semantic cache entries.

        Returns:
            Number of entries cleared
        """
        if paper_ids:
            pattern = f"{self.prefix}:*:{':'.join(sorted(paper_ids))}"
        else:
            pattern = f"{self.prefix}:*"

        count = 0
        try:
            async for key in redis_db.client.scan_iter(match=pattern):
                await redis_db.delete(key)
                count += 1
        except Exception as e:
            logger.warning(f"Error clearing semantic cache: {e}")
            return count

        logger.info(f"Cleared {count} semantic cache entries (pattern: {pattern})")
        return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about semantic cache.

        Returns:
            Dictionary with cache statistics
        """
        pattern = f"{self.prefix}:*"
        keys = []
        try:
            async for key in redis_db.client.scan_iter(match=pattern):
                keys.append(key)
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"total_entries": 0, "error": str(e)}

        return {
            "total_entries": len(keys),
            "threshold": self.threshold,
            "ttl": self.ttl,
        }
