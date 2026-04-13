"""Search API for external sources and library hybrid search.

Provides:
- External search: arXiv and Semantic Scholar
- Library search: Hybrid search over user's uploaded papers using dense + sparse + RRF
- Unified search: Merge and deduplicate results from multiple sources
- Multimodal search: Search across text, image, and table modalities with clustering
"""

import asyncio
import json
import math
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.config import settings
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.page_clustering import cluster_pages
from app.utils.logger import logger
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


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
    """Unified external search result format."""

    id: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    source: str
    pdfUrl: Optional[str] = None
    url: str
    citationCount: Optional[int] = None
    arxivId: Optional[str] = None


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
    dense_score: float = Field(0.0, description="Dense vector similarity score")
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
        await redis_client.setex(cache_key, ttl, json.dumps(results))
        logger.debug("Search cache set", cache_key=cache_key, ttl=ttl)
    except Exception as e:
        logger.warning("Redis cache set failed", error=str(e), cache_key=cache_key)


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
    """Remove duplicates using arXiv ID + title similarity.

    Strategy:
    1. Exact arXiv ID match (highest priority)
    2. Title similarity > 90% (fallback)

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

        # Tier 2: Title similarity > 90%
        is_duplicate = any(
            fuzz.ratio(result.title.lower(), seen_title.lower()) > 90
            for seen_title in seen_titles
        )
        if is_duplicate:
            logger.debug("Deduplicating by title similarity", title=result.title[:50])
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


# =============================================================================
# External Search Endpoints
# =============================================================================


@router.get("/arxiv", response_model=SearchResponse)
async def search_arxiv(
    query: str,
    limit: int = Query(default=20, le=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """Search arXiv for papers.

    Uses the arXiv Atom API to search for papers.
    Results are cached in Redis for 24 hours.
    """
    cache_key = f"search:arxiv:{query}:{limit}:{offset}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("arXiv search cache hit", query=query, limit=limit)
        return SearchResponse(success=True, data=cached)

    logger.info("arXiv search cache miss", query=query, limit=limit)

    # Apply rate limiting
    await _arxiv_rate_limiter.acquire()

    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": offset,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("arXiv API rate limited", query=query, status_code=429)
                _arxiv_rate_limiter.record_failure()
                return SearchResponse(success=True, data={"results": [], "total": 0})

            response.raise_for_status()
            _arxiv_rate_limiter.record_success()

        # Parse Atom XML response
        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)

        # Define namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        }

        total = 0
        total_elem = root.find("opensearch:totalResults", ns)
        if total_elem is not None and total_elem.text:
            total = int(total_elem.text)

        results = []
        for entry in root.findall("atom:entry", ns):
            # Extract ID from URL
            id_url = entry.findtext("atom:id", "", ns)
            arxiv_id = id_url.split("/")[-1] if id_url else ""

            # Remove version suffix if present
            if "v" in arxiv_id:
                arxiv_id = arxiv_id.split("v")[0]

            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name)

            # Extract published date for year
            published = entry.findtext("atom:published", "", ns)
            year = int(published[:4]) if published and len(published) >= 4 else 0

            # Get PDF link
            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            # Get primary category
            primary_category = entry.find("arxiv:primary_category", ns)
            category = (
                primary_category.get("term") if primary_category is not None else ""
            )

            results.append(
                SearchResult(
                    id=arxiv_id,
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=summary,
                    source="arxiv",
                    pdfUrl=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    url=id_url or f"https://arxiv.org/abs/{arxiv_id}",
                    citationCount=None,
                    arxivId=arxiv_id,
                )
            )

        result_data = {"results": results, "total": total}

        await set_search_cache(cache_key, result_data)
        logger.info(
            "arXiv search results cached",
            query=query,
            result_count=len(results),
            total=total,
        )

        return SearchResponse(success=True, data=result_data)

    except httpx.HTTPStatusError as e:
        logger.error(
            "arXiv API HTTP error",
            query=query,
            status_code=e.response.status_code,
            error=str(e),
        )
        _arxiv_rate_limiter.record_failure()
        return SearchResponse(success=True, data={"results": [], "total": 0})
    except Exception as e:
        logger.error(
            "arXiv search failed",
            query=query,
            error=str(e),
            error_type=type(e).__name__,
        )
        return SearchResponse(success=True, data={"results": [], "total": 0})


@router.get("/semantic-scholar", response_model=SearchResponse)
async def search_semantic_scholar(
    query: str,
    limit: int = Query(default=20, le=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """Search Semantic Scholar for papers.

    Uses the Semantic Scholar API to search for papers.
    Results are cached in Redis for 24 hours.
    """
    cache_key = f"search:s2:{query}:{limit}:{offset}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Semantic Scholar search cache hit", query=query, limit=limit)
        return SearchResponse(success=True, data=cached)

    logger.info("Semantic Scholar search cache miss", query=query, limit=limit)

    # Apply rate limiting
    await _s2_rate_limiter.acquire()

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"x-api-key": api_key} if api_key else {}

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "fields": "title,authors,year,abstract,openAccessPdf,externalIds,citationCount",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(
                    "Semantic Scholar API rate limited", query=query, status_code=429
                )
                _s2_rate_limiter.record_failure()
                return SearchResponse(success=True, data={"results": [], "total": 0})

            response.raise_for_status()
            _s2_rate_limiter.record_success()

        data = response.json()
        papers = data.get("data", [])
        total = data.get("total", len(papers))

        results = []
        for paper in papers:
            # Extract paper ID
            paper_id = paper.get("paperId", "")

            # Extract authors
            authors = []
            for author in paper.get("authors", []):
                name = author.get("name")
                if name:
                    authors.append(name)

            # Get PDF URL
            open_access = paper.get("openAccessPdf", {}) or {}
            pdf_url = open_access.get("url") if open_access else None

            # Get external IDs
            external_ids = paper.get("externalIds", {}) or {}
            arxiv_id = external_ids.get("ArXiv")

            results.append(
                SearchResult(
                    id=paper_id,
                    title=paper.get("title", "Unknown Title"),
                    authors=authors,
                    year=paper.get("year") or 0,
                    abstract=paper.get("abstract") or "No abstract available",
                    source="semantic-scholar",
                    pdfUrl=pdf_url,
                    url=f"https://www.semanticscholar.org/paper/{paper_id}",
                    citationCount=paper.get("citationCount"),
                    arxivId=arxiv_id,
                )
            )

        result_data = {"results": results, "total": total}

        await set_search_cache(cache_key, result_data)
        logger.info(
            "Semantic Scholar search results cached",
            query=query,
            result_count=len(results),
            total=total,
        )

        return SearchResponse(success=True, data=result_data)

    except httpx.HTTPStatusError as e:
        logger.error(
            "Semantic Scholar API HTTP error",
            query=query,
            status_code=e.response.status_code,
            error=str(e),
        )
        _s2_rate_limiter.record_failure()
        return SearchResponse(success=True, data={"results": [], "total": 0})
    except Exception as e:
        logger.error(
            "Semantic Scholar search failed",
            query=query,
            error=str(e),
            error_type=type(e).__name__,
        )
        return SearchResponse(success=True, data={"results": [], "total": 0})


@router.get("/doi/{doi:path}")
async def resolve_doi(doi: str):
    """Resolve DOI to paper metadata via CrossRef API.

    Args:
        doi: DOI identifier (e.g., "10.1038/nature12373")

    Returns:
        SearchResponse with paper metadata (title, authors, year, abstract)

    Raises:
        HTTPException: 404 if DOI not found

    Example:
        GET /search/doi/10.1038/nature12373
        Returns: {
            "success": true,
            "data": {
                "id": "10.1038/nature12373",
                "title": "The DNA sequence...",
                ...
            }
        }
    """
    from app.core.crossref_service import CrossRefService

    service = CrossRefService()
    redis_client = await get_redis_client()

    result = await service.resolve_doi(doi, redis_client)
    return {"success": True, "data": result}


# =============================================================================
# Library Search Endpoint (Milvus-based)
# =============================================================================


@router.get("/library", response_model=LibrarySearchResponse)
async def search_library(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    paper_ids: List[str] = Query(
        default=[], description="Specific paper IDs to search (optional)"
    ),
    limit: int = Query(
        default=10, description="Maximum results to return", ge=1, le=50
    ),
    user_id: str = CurrentUserId,
) -> Dict[str, Any]:
    """Search within user's library using Milvus vector search.

    Performs semantic search using Milvus with BGE-M3 embeddings.
    MultimodalSearchService handles intent detection and optional reranking.

    Args:
        q: Search query text
        paper_ids: Optional list of specific paper IDs to search within
        limit: Maximum number of results to return
        user_id: Authenticated user ID

    Returns:
        LibrarySearchResponse with ranked chunk results
    """
    logger.info(
        "Library search initiated",
        query=q[:50],
        paper_count=len(paper_ids),
        user_id=user_id,
    )

    # If no paper_ids provided, search would return empty
    if not paper_ids:
        logger.warning("No paper_ids provided for library search")
        return LibrarySearchResponse(
            success=True,
            data={
                "query": q,
                "paperCount": 0,
                "resultCount": 0,
                "weights": {"dense": 1.0, "sparse": 0.0},
                "results": [],
            },
        )

    try:
        # Use MultimodalSearchService for unified search
        result = await get_multimodal_search_service().search(
            query=q,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=limit,
            use_reranker=True,
        )

        # Transform results to response format
        library_results = []
        for r in result.get("results", []):
            library_results.append(
                LibrarySearchResult(
                    id=str(r.get("id", "")),
                    paper_id=r.get("paper_id", ""),
                    content=r.get("content_data", "")[:500]
                    if r.get("content_data")
                    else "",
                    section=r.get("section"),
                    page=r.get("page_num"),
                    rrf_score=r.get("reranker_score", r.get("distance", 0.0)),
                    dense_score=r.get("distance", 0.0),
                    sparse_score=0.0,  # Not used in Milvus-only search
                    dense_rank=None,
                    sparse_rank=None,
                )
            )

        logger.info(
            "Library search completed",
            query=q[:50],
            results_found=len(library_results),
        )

        return LibrarySearchResponse(
            success=True,
            data={
                "query": q,
                "paperCount": len(paper_ids),
                "resultCount": len(library_results),
                "weights": {"dense": 1.0, "sparse": 0.0},
                "results": [
                    {
                        "id": r.id,
                        "paperId": r.paper_id,
                        "content": r.content,
                        "section": r.section,
                        "page": r.page,
                        "rrfScore": r.rrf_score,
                        "denseScore": r.dense_score,
                        "sparseScore": r.sparse_score,
                    }
                    for r in library_results
                ],
            },
        )

    except Exception as e:
        logger.error("Library search failed", error=str(e), query=q[:50])
        raise HTTPException(
            status_code=500, detail=Errors.internal(f"Search failed: {str(e)}")
        )


# =============================================================================
# Unified Search Endpoint
# =============================================================================


@router.get("/unified", response_model=SearchResponse)
async def search_unified(
    query: str,
    limit: int = Query(default=20, le=50, ge=1),
    offset: int = Query(default=0, ge=0),
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Dict[str, Any]:
    """Search both arXiv and Semantic Scholar, return merged results.

    Query params:
    - query: Search query string
    - limit: Max results (1-50, default 20)
    - offset: Pagination offset (default 0)
    - year_from: Filter papers from this year (inclusive)
    - year_to: Filter papers to this year (inclusive)

    Results are:
    1. Fetched from both sources in parallel
    2. Merged and deduplicated (by arXiv ID + title similarity)
    3. Filtered by year range
    4. Sorted by citation-based composite score
    """
    cache_key = f"search:unified:{query}:{limit}:{offset}:{year_from}:{year_to}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Unified search cache hit", query=query, limit=limit)
        return SearchResponse(success=True, data=cached)

    logger.info(
        "Unified search initiated",
        query=query,
        limit=limit,
        year_from=year_from,
        year_to=year_to,
    )

    # Parallel search with error handling
    arxiv_task = search_arxiv(query, limit=limit, offset=offset)
    s2_task = search_semantic_scholar(query, limit=limit, offset=offset)

    results = await asyncio.gather(arxiv_task, s2_task, return_exceptions=True)

    arxiv_list: List[SearchResult] = []
    s2_list: List[SearchResult] = []
    arxiv_total = 0
    s2_total = 0

    if isinstance(results[0], Exception):
        logger.warning(f"arXiv search failed: {results[0]}")
    else:
        # Handle SearchResponse wrapper
        arxiv_data = results[0].data if hasattr(results[0], "data") else results[0]
        arxiv_list = arxiv_data.get("results", [])
        arxiv_total = arxiv_data.get("total", 0)

    if isinstance(results[1], Exception):
        logger.warning(f"Semantic Scholar search failed: {results[1]}")
    else:
        # Handle SearchResponse wrapper
        s2_data = results[1].data if hasattr(results[1], "data") else results[1]
        s2_list = s2_data.get("results", [])
        s2_total = s2_data.get("total", 0)

    # Merge and deduplicate
    all_results = arxiv_list + s2_list
    unique_results = deduplicate_results(all_results)

    # Apply year filters
    if year_from is not None:
        unique_results = [r for r in unique_results if r.year >= year_from]
    if year_to is not None:
        unique_results = [r for r in unique_results if r.year <= year_to]

    # Score and sort by citation-based ranking
    scored_results = sorted(
        unique_results,
        key=lambda r: calculate_paper_score(
            getattr(r, "citationCount", None), r.year, relevance=0.5
        ),
        reverse=True,
    )

    total = arxiv_total + s2_total
    result_data = {"results": scored_results[:limit], "total": total}

    await set_search_cache(cache_key, result_data)
    logger.info(
        "Unified search complete",
        query=query,
        total_results=len(all_results),
        unique_results=len(unique_results),
        returned_results=len(result_data["results"]),
    )

    return SearchResponse(success=True, data=result_data)


# =============================================================================
# Multimodal Search Models
# =============================================================================


class MultimodalSearchRequest(BaseModel):
    """Multimodal search request model."""

    query: str = Field(
        ..., description="Search query string", min_length=1, max_length=500
    )
    paper_ids: List[str] = Field(..., description="List of paper IDs to search within")
    top_k: int = Field(default=10, description="Maximum results to return", ge=1, le=50)
    use_reranker: bool = Field(default=True, description="Whether to apply reranking")
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content types to search (text, image, table)",
    )
    enable_clustering: bool = Field(
        default=True, description="Whether to cluster results by page"
    )


class ClusterResult(BaseModel):
    """Cluster result model."""

    cluster_id: int = Field(..., description="Cluster identifier")
    pages: List[int] = Field(..., description="Page numbers in this cluster")
    results: List[Dict[str, Any]] = Field(
        ..., description="Search results in this cluster"
    )


class MultimodalSearchResponse(BaseModel):
    """Multimodal search response model (unified wrapper)."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Multimodal Search Endpoint
# =============================================================================


@router.post("/multimodal", response_model=MultimodalSearchResponse)
async def multimodal_search(
    request: MultimodalSearchRequest,
    user_id: str = CurrentUserId,
) -> Dict[str, Any]:
    """Multimodal search across text, images, and tables.

    Supports intent detection, weighted fusion, and optional reranking.
    Results organized by page clusters when enable_clustering=True.

    Args:
        request: MultimodalSearchRequest with query, paper_ids, and options
        user_id: Authenticated user ID

    Returns:
        MultimodalSearchResponse with query, intent, clusters, and results

    Example:
        POST /api/search/multimodal
        {
            "query": "YOLO architecture diagram",
            "paper_ids": ["paper-1", "paper-2"],
            "top_k": 10,
            "use_reranker": true,
            "enable_clustering": true
        }
    """
    logger.info(
        "Multimodal search initiated",
        query=request.query[:50],
        paper_count=len(request.paper_ids),
        top_k=request.top_k,
        use_reranker=request.use_reranker,
        enable_clustering=request.enable_clustering,
        user_id=user_id,
    )

    try:
        # Get multimodal search service
        service = get_multimodal_search_service()

        # Execute search
        result = await service.search(
            query=request.query,
            paper_ids=request.paper_ids,
            user_id=user_id,
            top_k=request.top_k,
            use_reranker=request.use_reranker,
            content_types=request.content_types,
        )

        # Apply page clustering if enabled
        if request.enable_clustering and result["results"]:
            try:
                clusters = cluster_pages(result["results"])

                # Format clusters for response
                cluster_list = [
                    ClusterResult(
                        cluster_id=cid,
                        pages=list(set(r.get("page_num", 0) for r in results)),
                        results=results,
                    )
                    for cid, results in clusters.items()
                ]

                result["clusters"] = cluster_list

                logger.info(
                    "Page clustering applied",
                    cluster_count=len(clusters),
                    result_count=len(result["results"]),
                )
            except Exception as e:
                logger.warning(
                    "Page clustering failed, returning unclustered results",
                    error=str(e),
                )
                # Continue without clustering

        return MultimodalSearchResponse(
            success=True,
            data={
                "query": result.get("query", request.query),
                "intent": result.get("intent", "default"),
                "queryIntent": result.get("query_intent"),
                "weights": result.get("weights", {}),
                "clusters": [
                    {
                        "clusterId": c.cluster_id,
                        "pages": list(c.pages),
                        "results": c.results,
                    }
                    for c in result.get("clusters", [])
                ]
                if "clusters" in result
                else None,
                "results": result.get("results", []),
                "totalCount": result.get("total_count", len(result.get("results", []))),
            },
        )

    except Exception as e:
        logger.error("Multimodal search failed", error=str(e), query=request.query[:50])
        raise HTTPException(
            status_code=500,
            detail=Errors.internal(f"Multimodal search failed: {str(e)}"),
        )


# =============================================================================
# Fusion Search Endpoint
# =============================================================================


@router.post("/fusion", response_model=FusionSearchResponse)
async def fusion_search(
    request: FusionSearchRequest,
    user_id: str = CurrentUserId,
) -> FusionSearchResponse:
    """Unified search across library + external sources with merging and deduplication.

    Searches user's library (Milvus) AND external APIs (arXiv, Semantic Scholar).
    Results are merged, deduplicated, and ranked by citation score.

    Args:
        request: FusionSearchRequest with query, paper_ids, limit, sources
        user_id: Authenticated user ID

    Returns:
        FusionSearchResponse with merged results, source status, and warnings

    Degradation Strategy:
        - If external API fails: continue with other sources
        - If library search fails: return external results only
        - Track failures in warnings and sources.status

    Example:
        POST /search/fusion
        {
            "query": "transformer architecture",
            "paper_ids": ["paper-1", "paper-2"],
            "limit": 20,
            "sources": ["library", "arxiv", "semantic_scholar"]
        }
    """
    logger.info(
        "Fusion search initiated",
        query=request.query[:50],
        paper_count=len(request.paper_ids),
        sources=request.sources,
        user_id=user_id,
    )

    results: List[SearchResult] = []
    sources_status: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    # Prepare parallel search tasks
    tasks = []

    # 1. Library search (Milvus)
    if "library" in request.sources and request.paper_ids:

        async def search_library_internal():
            from app.core.multimodal_search_service import get_multimodal_search_service

            service = get_multimodal_search_service()
            result = await service.search(
                query=request.query,
                paper_ids=request.paper_ids,
                user_id=user_id,  # Use authenticated user_id
                top_k=20,  # Fetch more for dedup
                use_reranker=True,
            )

            # Transform to SearchResult format
            library_results = []
            for r in result.get("results", []):
                library_results.append(
                    SearchResult(
                        id=r.get("id", ""),
                        title=r.get("title", "Unknown"),
                        authors=[],  # Library chunks don't have authors
                        year=r.get("year", 0),
                        abstract=r.get("content_data", "")[:500],
                        source="library",
                        url="",  # Internal papers don't have URL
                        pdfUrl=None,
                        citationCount=None,
                        arxivId=None,
                    )
                )
            return library_results

        tasks.append(("library", search_library_internal()))

    # 2. arXiv search
    if "arxiv" in request.sources:
        tasks.append(("arxiv", search_arxiv(query=request.query, limit=10)))

    # 3. Semantic Scholar search
    if "semantic_scholar" in request.sources:
        tasks.append(
            ("semantic_scholar", search_semantic_scholar(query=request.query, limit=10))
        )

    # Execute all searches in parallel with error handling
    search_results = await asyncio.gather(
        *[task[1] for task in tasks], return_exceptions=True
    )

    # Process results
    for (source_name, _), result in zip(tasks, search_results):
        if isinstance(result, Exception):
            error_msg = f"{source_name} search failed: {str(result)}"
            warnings.append(error_msg)
            sources_status[source_name] = {
                "count": 0,
                "success": False,
                "error": str(result),
            }
            logger.warning(
                "Search source failed",
                source=source_name,
                error=str(result),
            )
        else:
            # Extract results
            if source_name == "library":
                source_results = result  # Already List[SearchResult]
            else:
                # External search returns SearchResponse with data wrapper
                if hasattr(result, "data"):
                    source_results = result.data.get("results", [])
                else:
                    source_results = result.get("results", [])

            # Mark external results
            for r in source_results:
                if source_name != "library":
                    r.in_library = False

            results.extend(source_results)
            sources_status[source_name] = {
                "count": len(source_results),
                "success": True,
            }

    # Deduplicate results (arXiv ID + title similarity)
    unique_results = deduplicate_results(results)

    # Score and sort
    scored_results = sorted(
        unique_results,
        key=lambda r: calculate_paper_score(
            r.citationCount,
            r.year,
            relevance=1.0
            if r.source == "library"
            else 0.5,  # D-05: internal > external
        ),
        reverse=True,
    )

    logger.info(
        "Fusion search complete",
        query=request.query[:50],
        total_results=len(results),
        unique_results=len(unique_results),
        returned=len(scored_results[: request.limit]),
    )

    return FusionSearchResponse(
        success=True,
        data={
            "query": request.query,
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "source": r.source,
                    "pdfUrl": r.pdfUrl,
                    "url": r.url,
                    "citationCount": r.citationCount,
                    "arxivId": r.arxivId,
                }
                for r in scored_results[: request.limit]
            ],
            "sources": sources_status,
            "warnings": warnings,
        },
    )
