"""Shared infrastructure for search operations.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
Shared components used by all search sub-modules.

Contains:
- RateLimiter: Token bucket rate limiting for external APIs
- Response models: SearchResult, SearchResponse, FusionSearchRequest, etc.
- Cache helpers: Redis-based caching for search results
- Scoring: Citation-based paper ranking
- Deduplication: Remove duplicate results by arXiv ID + title
"""

import asyncio
import json
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.config import settings
from app.utils.logger import logger


# =============================================================================
# Rate Limiting for External APIs
# =============================================================================


class RateLimiter:
    """Rate limiter for external API calls with exponential backoff.

    Implements:
    - Token bucket algorithm for rate limiting
    - Exponential backoff on 429 errors
    - Per-API rate limit configuration
    """

    def __init__(self, min_interval: float, max_backoff: float = 60.0):
        """Initialize rate limiter.

        Args:
            min_interval: Minimum seconds between requests
            max_backoff: Maximum backoff time in seconds
        """
        self.min_interval = min_interval
        self.max_backoff = max_backoff
        self.last_request_time = 0.0
        self.consecutive_failures = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request.

        Waits if necessary to respect rate limit.
        Implements exponential backoff after failures.
        """
        async with self._lock:
            now = time.time()

            # Calculate wait time
            if self.consecutive_failures > 0:
                # Exponential backoff: 1s, 2s, 4s, 8s, ...
                backoff = min((2**self.consecutive_failures) * 1.0, self.max_backoff)
                wait_time = max(0, self.last_request_time + backoff - now)
            else:
                # Normal rate limit
                wait_time = max(0, self.last_request_time + self.min_interval - now)

            if wait_time > 0:
                logger.debug(
                    "Rate limiter waiting",
                    wait_seconds=wait_time,
                    consecutive_failures=self.consecutive_failures,
                )
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def record_success(self):
        """Record successful request, reset failure counter."""
        self.consecutive_failures = 0

    def record_failure(self):
        """Record failed request, increment failure counter."""
        self.consecutive_failures += 1
        logger.warning(
            "Rate limiter recorded failure",
            consecutive_failures=self.consecutive_failures,
        )


# Global rate limiters for each API
# arXiv: max 1 request per 3 seconds
_arxiv_rate_limiter = RateLimiter(min_interval=3.0, max_backoff=60.0)

# Semantic Scholar: max 1 request per 1 second
_s2_rate_limiter = RateLimiter(min_interval=1.0, max_backoff=30.0)


# =============================================================================
# External Search Models
# =============================================================================


class SearchResult(BaseModel):
        """Unified external search result format (canonical ExternalPaper shape).

        WP0: This is the canonical ExternalPaper model shared by search results
        and import preview. availability and libraryStatus are the two key fields
        that front-end uses to decide which CTA to show.

        availability:
            metadata_only     - no PDF source found
            pdf_available     - open-access PDF exists
            pdf_unavailable   - PDF exists in provider but is not open-access

        libraryStatus:
            not_imported            - paper not in user's KB
            importing               - ImportJob in progress
            imported_metadata_only  - paper in KB but not fulltext-indexed
            imported_fulltext_ready - paper fully indexed (chunk+embed+milvus)
        """

        id: str
        title: str
        authors: List[str]
        year: int
        abstract: str
        source: str  # arxiv | s2
        pdfUrl: Optional[str] = None
        url: str
        citationCount: Optional[int] = None
        arxivId: Optional[str] = None
        # WP0 canonical fields
        s2PaperId: Optional[str] = None
        doi: Optional[str] = None
        venue: Optional[str] = None
        openAccess: bool = False
        fieldsOfStudy: List[str] = []
        availability: str = "metadata_only"  # metadata_only | pdf_available | pdf_unavailable
        libraryStatus: str = "not_imported"  # not_imported | importing | imported_metadata_only | imported_fulltext_ready
        in_library: bool = False  # legacy field kept for backward compat


class SearchResponse(BaseModel):
    """External search response format (unified wrapper)."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Library Search Models
# =============================================================================


class LibrarySearchResult(BaseModel):
    """Library hybrid search result (chunk-level)."""

    id: str = Field(..., description="Chunk ID")
    paper_id: str = Field(..., description="Paper ID")
    content: str = Field(..., description="Chunk content preview")
    section: Optional[str] = Field(
        None, description="Section name (Introduction/Method/etc)"
    )
    page: Optional[int] = Field(None, description="Page number")
    rrf_score: float = Field(..., description="RRF fusion score")
    dense_score: float = Field(0.0, description="Dense vector relevance score")
    sparse_score: float = Field(0.0, description="Sparse text search score")
    dense_rank: Optional[int] = Field(None, description="Rank in dense results")
    sparse_rank: Optional[int] = Field(None, description="Rank in sparse results")


class LibrarySearchResponse(BaseModel):
    """Library hybrid search response (unified wrapper)."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Fusion Search Models
# =============================================================================


class FusionSearchRequest(BaseModel):
    """Fusion search request combining library + external sources."""

    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    paper_ids: List[str] = Field(
        default=[], description="User's library paper IDs to search"
    )
    limit: int = Field(default=20, description="Maximum results to return", ge=1, le=50)
    sources: List[str] = Field(
        default=["library", "arxiv", "semantic_scholar"],
        description="Sources to search (library, arxiv, semantic_scholar)",
    )


class FusionSearchResponse(BaseModel):
    """Fusion search response with merged results (unified wrapper)."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Redis Client Helper
# =============================================================================


_redis_client = None


async def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as redis

        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            # Note: socket_read_timeout not supported in this Redis version
            health_check_interval=30,
        )
    return _redis_client


async def get_search_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached search results from Redis.

    Args:
        cache_key: Redis key for the search query

    Returns:
        Cached results dict or None if not found
    """
    try:
        redis_client = await get_redis_client()
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug("Search cache hit", cache_key=cache_key)
            return json.loads(cached)
    except Exception as e:
        logger.warning("Redis cache get failed", error=str(e), cache_key=cache_key)
    return None


async def set_search_cache(
    cache_key: str, results: Dict[str, Any], ttl: int = 86400
) -> None:
    """Cache search results in Redis.

    Args:
        cache_key: Redis key for the search query
        results: Results dict to cache
        ttl: Time-to-live in seconds (default: 24 hours)
    """
    try:
        redis_client = await get_redis_client()
        await redis_client.setex(cache_key, ttl, json.dumps(_json_safe(results)))
        logger.debug("Search cache set", cache_key=cache_key, ttl=ttl)
    except Exception as e:
        logger.warning("Redis cache set failed", error=str(e), cache_key=cache_key)


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


# =============================================================================
# Citation-Based Scoring
# =============================================================================


def calculate_paper_score(
    citation_count: Optional[int], year: int, relevance: float = 0.5
) -> float:
    """Calculate composite score for paper ranking.

    Formula: citation_score * 0.5 + recency_score * 0.3 + relevance * 0.2

    Args:
        citation_count: Number of citations (None if unknown)
        year: Publication year
        relevance: Relevance score from search (0.0-1.0)

    Returns:
        Composite score (higher is better)
    """
    # Citation score: log scale to handle wide ranges, normalized
    # citation_score = min(log10(citations + 1) / 5, 1.0)  # Cap at ~100K citations
    citations = citation_count or 0
    citation_score = min(math.log10(citations + 1) / 5, 1.0)

    # Recency score: newer papers get higher scores
    # recency_score = exp(-year_diff / 10)  # Half-life of 10 years
    current_year = datetime.now().year
    year_diff = max(0, current_year - year)
    recency_score = math.exp(-year_diff / 10)

    # Weighted combination per plan specification
    score = citation_score * 0.5 + recency_score * 0.3 + relevance * 0.2
    return score


# =============================================================================
# Deduplication Logic
# =============================================================================


def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicates using arXiv ID + title overlap score.

    Strategy:
    1. Exact arXiv ID match (highest priority)
    2. Title overlap score > 90% (fallback)

    Prefers Semantic Scholar results when available (more metadata).

    Args:
        results: List of search results from multiple sources

    Returns:
        List of unique search results
    """
    seen_arxiv_ids: set[str] = set()
    seen_titles: list[str] = []
    unique_results: list[SearchResult] = []

    # Sort so S2 results (with more metadata) are preferred
    sorted_results = sorted(
        results, key=lambda r: 0 if r.source == "semantic-scholar" else 1
    )

    for result in sorted_results:
        # Tier 1: Exact arXiv ID match
        if result.arxivId:
            if result.arxivId in seen_arxiv_ids:
                logger.debug(
                    "Deduplicating by arXiv ID",
                    arxiv_id=result.arxivId,
                    title=result.title[:50],
                )
                continue
            seen_arxiv_ids.add(result.arxivId)

        # Tier 2: Title overlap score > 90%
        is_duplicate = any(
            fuzz.ratio(result.title.lower(), seen_title.lower()) > 90
            for seen_title in seen_titles
        )
        if is_duplicate:
            logger.debug("Deduplicating by title overlap score", title=result.title[:50])
            continue

        seen_titles.append(result.title)
        unique_results.append(result)

    logger.info(
        "Deduplication complete",
        input_count=len(results),
        output_count=len(unique_results),
        duplicates_removed=len(results) - len(unique_results),
    )

    return unique_results


__all__ = [
    "RateLimiter",
    "_arxiv_rate_limiter",
    "_s2_rate_limiter",
    "SearchResult",
    "SearchResponse",
    "LibrarySearchResult",
    "LibrarySearchResponse",
    "FusionSearchRequest",
    "FusionSearchResponse",
    "get_redis_client",
    "get_search_cache",
    "set_search_cache",
    "calculate_paper_score",
    "deduplicate_results",
]
