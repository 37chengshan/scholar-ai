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
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.core.config import settings
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.page_clustering import cluster_pages
from app.utils.logger import logger

router = APIRouter()


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
    """External search response format."""

    results: List[SearchResult]


# =============================================================================
# Library Search Models
# =============================================================================

class LibrarySearchResult(BaseModel):
    """Library hybrid search result (chunk-level)."""

    id: str = Field(..., description="Chunk ID")
    paper_id: str = Field(..., description="Paper ID")
    content: str = Field(..., description="Chunk content preview")
    section: Optional[str] = Field(None, description="Section name (Introduction/Method/etc)")
    page: Optional[int] = Field(None, description="Page number")
    rrf_score: float = Field(..., description="RRF fusion score")
    dense_score: float = Field(0.0, description="Dense vector similarity score")
    sparse_score: float = Field(0.0, description="Sparse text search score")
    dense_rank: Optional[int] = Field(None, description="Rank in dense results")
    sparse_rank: Optional[int] = Field(None, description="Rank in sparse results")


class LibrarySearchResponse(BaseModel):
    """Library hybrid search response."""

    query: str = Field(..., description="Search query")
    paper_count: int = Field(..., description="Number of papers searched")
    result_count: int = Field(..., description="Number of results returned")
    weights: Dict[str, float] = Field(..., description="Fusion weights used")
    results: List[LibrarySearchResult] = Field(..., description="Search results")


# =============================================================================
# Fusion Search Models
# =============================================================================


class FusionSearchRequest(BaseModel):
    """Fusion search request combining library + external sources."""

    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    paper_ids: List[str] = Field(default=[], description="User's library paper IDs to search")
    limit: int = Field(default=20, description="Maximum results to return", ge=1, le=50)
    sources: List[str] = Field(
        default=["library", "arxiv", "semantic_scholar"],
        description="Sources to search (library, arxiv, semantic_scholar)"
    )


class FusionSearchResponse(BaseModel):
    """Fusion search response with merged results."""

    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Merged and ranked results")
    sources: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Per-source status {count, success, error?}"
    )
    warnings: List[str] = Field(default=[], description="Warnings for failed sources")


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
            socket_read_timeout=5,
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


async def set_search_cache(cache_key: str, results: Dict[str, Any], ttl: int = 86400) -> None:
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
    citation_count: Optional[int],
    year: int,
    relevance: float = 0.5
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
        results,
        key=lambda r: (0 if r.source == "semantic-scholar" else 1)
    )

    for result in sorted_results:
        # Tier 1: Exact arXiv ID match
        if result.arxivId:
            if result.arxivId in seen_arxiv_ids:
                logger.debug(
                    "Deduplicating by arXiv ID",
                    arxiv_id=result.arxivId,
                    title=result.title[:50]
                )
                continue
            seen_arxiv_ids.add(result.arxivId)

        # Tier 2: Title similarity > 90%
        is_duplicate = any(
            fuzz.ratio(result.title.lower(), seen_title.lower()) > 90
            for seen_title in seen_titles
        )
        if is_duplicate:
            logger.debug(
                "Deduplicating by title similarity",
                title=result.title[:50]
            )
            continue

        seen_titles.append(result.title)
        unique_results.append(result)

    logger.info(
        "Deduplication complete",
        input_count=len(results),
        output_count=len(unique_results),
        duplicates_removed=len(results) - len(unique_results)
    )

    return unique_results


# =============================================================================
# Authentication Dependency (placeholder - will be replaced by actual auth)
# =============================================================================

async def get_current_user_id() -> str:
    """Get current user ID from auth token.

    In production, this validates JWT and returns user ID.
    For now, returns a placeholder for API structure.
    """
    # This will be replaced by actual auth middleware
    return "placeholder-user-id"


# =============================================================================
# External Search Endpoints
# =============================================================================


@router.get("/arxiv", response_model=SearchResponse)
async def search_arxiv(
    query: str,
    limit: int = Query(default=10, le=50, ge=1),
) -> Dict[str, Any]:
    """Search arXiv for papers.

    Uses the arXiv Atom API to search for papers.
    Results are cached in Redis for 24 hours.
    """
    cache_key = f"search:arxiv:{query}:{limit}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("arXiv search cache hit", query=query, limit=limit)
        return cached

    logger.info("arXiv search cache miss", query=query, limit=limit)

    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

        # Parse Atom XML response
        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)

        # Define namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

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
            category = primary_category.get("term") if primary_category is not None else ""

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

        result_data = {"results": results}

        # Cache the results
        await set_search_cache(cache_key, result_data)
        logger.info("arXiv search results cached", query=query, result_count=len(results))

        return result_data


@router.get("/semantic-scholar", response_model=SearchResponse)
async def search_semantic_scholar(
    query: str,
    limit: int = Query(default=10, le=50, ge=1),
) -> Dict[str, Any]:
    """Search Semantic Scholar for papers.

    Uses the Semantic Scholar API to search for papers.
    Results are cached in Redis for 24 hours.
    """
    cache_key = f"search:s2:{query}:{limit}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Semantic Scholar search cache hit", query=query, limit=limit)
        return cached

    logger.info("Semantic Scholar search cache miss", query=query, limit=limit)

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"X-API-KEY": api_key} if api_key else {}

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,openAccessPdf,externalIds,citationCount",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        papers = data.get("data", [])

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

        result_data = {"results": results}

        # Cache the results
        await set_search_cache(cache_key, result_data)
        logger.info("Semantic Scholar search results cached", query=query, result_count=len(results))

        return result_data


@router.get("/doi/{doi:path}", response_model=SearchResult)
async def resolve_doi(doi: str):
    """Resolve DOI to paper metadata via CrossRef API.

    Args:
        doi: DOI identifier (e.g., "10.1038/nature12373")

    Returns:
        SearchResult with paper metadata (title, authors, year, abstract)

    Raises:
        HTTPException: 404 if DOI not found

    Example:
        GET /search/doi/10.1038/nature12373
        Returns: {
            "id": "10.1038/nature12373",
            "title": "The DNA sequence...",
            "authors": ["John Doe"],
            "year": 2001,
            ...
        }
    """
    from app.core.crossref_service import CrossRefService

    service = CrossRefService()
    redis_client = await get_redis_client()

    result = await service.resolve_doi(doi, redis_client)
    return SearchResult(**result)


# =============================================================================
# Library Search Endpoint (Hybrid Search)
# =============================================================================


@router.get("/library", response_model=LibrarySearchResponse)
async def search_library(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    paper_ids: List[str] = Query(default=[], description="Specific paper IDs to search (optional)"),
    limit: int = Query(default=10, description="Maximum results to return", ge=1, le=50),
    hybrid: bool = Query(default=True, description="Use hybrid search (dense + sparse + RRF)"),
    dense_weight: float = Query(default=0.6, description="Weight for dense search (0.0-1.0)", ge=0.0, le=1.0),
    sparse_weight: float = Query(default=0.4, description="Weight for sparse search (0.0-1.0)", ge=0.0, le=1.0),
    # user_id: str = Depends(get_current_user_id),  # Auth placeholder
) -> Dict[str, Any]:
    """Search within user's library using hybrid search.

    Performs hybrid search combining:
    - Dense: PGVector cosine similarity (semantic understanding)
    - Sparse: PostgreSQL tsvector full-text search (lexical matching)
    - RRF: Reciprocal Rank Fusion with configurable weights

    Default weights: 0.6 dense / 0.4 sparse (semantic priority)

    Args:
        q: Search query text
        paper_ids: Optional list of specific paper IDs to search within
        limit: Maximum number of results to return
        hybrid: If True, use hybrid search; else dense only
        dense_weight: Weight for dense results in RRF fusion
        sparse_weight: Weight for sparse results in RRF fusion

    Returns:
        LibrarySearchResponse with ranked chunk results
    """
    from app.core.hybrid_search import HybridSearchService
    from app.core.database import get_db_connection

    logger.info(
        "Library search initiated",
        query=q[:50],
        paper_count=len(paper_ids),
        hybrid=hybrid,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
    )

    # Validate weights sum to approximately 1.0
    total_weight = dense_weight + sparse_weight
    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=422,
            detail=f"Weights must sum to 1.0, got {total_weight}"
        )

    # If no paper_ids provided, search would return empty
    # In production, this would query user's papers from database
    if not paper_ids:
        logger.warning("No paper_ids provided for library search")
        return {
            "query": q,
            "paper_count": 0,
            "result_count": 0,
            "weights": {"dense": dense_weight, "sparse": sparse_weight},
            "results": [],
        }

    try:
        async with get_db_connection() as conn:
            service = HybridSearchService(
                connection=conn,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
                rrf_k=60,
            )

            results = await service.search(
                query=q,
                paper_ids=paper_ids,
                limit=limit,
                use_hybrid=hybrid,
            )

        # Transform results to response format
        library_results = [
            LibrarySearchResult(
                id=r["id"],
                paper_id=r["paper_id"],
                content=r["content"][:500] if r.get("content") else "",  # Preview
                section=r.get("section"),
                page=r.get("page"),
                rrf_score=r["rrf_score"],
                dense_score=r.get("dense_score", 0.0),
                sparse_score=r.get("sparse_score", 0.0),
                dense_rank=r.get("dense_rank"),
                sparse_rank=r.get("sparse_rank"),
            )
            for r in results
        ]

        logger.info(
            "Library search completed",
            query=q[:50],
            results_found=len(library_results),
        )

        return {
            "query": q,
            "paper_count": len(paper_ids),
            "result_count": len(library_results),
            "weights": {"dense": dense_weight, "sparse": sparse_weight},
            "results": library_results,
        }

    except Exception as e:
        logger.error("Library search failed", error=str(e), query=q[:50])
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# =============================================================================
# Unified Search Endpoint
# =============================================================================


@router.get("/unified", response_model=SearchResponse)
async def search_unified(
    query: str,
    limit: int = Query(default=10, le=50, ge=1),
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Dict[str, Any]:
    """Search both arXiv and Semantic Scholar, return merged results.

    Query params:
    - query: Search query string
    - limit: Max results (1-50, default 10)
    - year_from: Filter papers from this year (inclusive)
    - year_to: Filter papers to this year (inclusive)

    Results are:
    1. Fetched from both sources in parallel
    2. Merged and deduplicated (by arXiv ID + title similarity)
    3. Filtered by year range
    4. Sorted by citation-based composite score
    """
    cache_key = f"search:unified:{query}:{limit}:{year_from}:{year_to}"

    # Check cache first
    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Unified search cache hit", query=query, limit=limit)
        return cached

    logger.info(
        "Unified search initiated",
        query=query,
        limit=limit,
        year_from=year_from,
        year_to=year_to
    )

    # Parallel search with error handling
    arxiv_task = search_arxiv(query, limit=limit)
    s2_task = search_semantic_scholar(query, limit=limit)

    results = await asyncio.gather(
        arxiv_task, s2_task, return_exceptions=True
    )

    # Extract results, handling errors gracefully
    arxiv_list: List[SearchResult] = []
    s2_list: List[SearchResult] = []

    if isinstance(results[0], Exception):
        logger.warning(f"arXiv search failed: {results[0]}")
    else:
        arxiv_list = results[0].get("results", [])

    if isinstance(results[1], Exception):
        logger.warning(f"Semantic Scholar search failed: {results[1]}")
    else:
        s2_list = results[1].get("results", [])

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
            getattr(r, 'citationCount', None),
            r.year,
            relevance=0.5
        ),
        reverse=True
    )

    result_data = {"results": scored_results[:limit]}

    # Cache the results
    await set_search_cache(cache_key, result_data)
    logger.info(
        "Unified search complete",
        query=query,
        total_results=len(all_results),
        unique_results=len(unique_results),
        returned_results=len(result_data["results"])
    )

    return result_data


# =============================================================================
# Multimodal Search Models
# =============================================================================


class MultimodalSearchRequest(BaseModel):
    """Multimodal search request model."""

    query: str = Field(..., description="Search query string", min_length=1, max_length=500)
    paper_ids: List[str] = Field(..., description="List of paper IDs to search within")
    top_k: int = Field(default=10, description="Maximum results to return", ge=1, le=50)
    use_reranker: bool = Field(default=True, description="Whether to apply reranking")
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content types to search (text, image, table)",
    )
    enable_clustering: bool = Field(default=True, description="Whether to cluster results by page")


class ClusterResult(BaseModel):
    """Cluster result model."""

    cluster_id: int = Field(..., description="Cluster identifier")
    pages: List[int] = Field(..., description="Page numbers in this cluster")
    results: List[Dict[str, Any]] = Field(..., description="Search results in this cluster")


class MultimodalSearchResponse(BaseModel):
    """Multimodal search response model."""

    query: str = Field(..., description="Search query")
    intent: str = Field(..., description="Detected query intent (default, image_weighted, table_weighted)")
    weights: Dict[str, float] = Field(..., description="Modality weights applied")
    clusters: Optional[List[ClusterResult]] = Field(None, description="Page clusters if enabled")
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results")


# =============================================================================
# Multimodal Search Endpoint
# =============================================================================


@router.post("/multimodal", response_model=MultimodalSearchResponse)
async def multimodal_search(
    request: MultimodalSearchRequest,
    # current_user: dict = Depends(get_current_user)  # Auth placeholder
) -> Dict[str, Any]:
    """Multimodal search across text, images, and tables.

    Supports intent detection, weighted fusion, and optional reranking.
    Results organized by page clusters when enable_clustering=True.

    Args:
        request: MultimodalSearchRequest with query, paper_ids, and options

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
    )

    try:
        # Get multimodal search service
        service = get_multimodal_search_service()

        # Execute search
        result = await service.search(
            query=request.query,
            paper_ids=request.paper_ids,
            user_id="placeholder-user-id",  # TODO: Get from auth
            top_k=request.top_k,
            use_reranker=request.use_reranker,
            content_types=request.content_types
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
                        results=results
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

        return MultimodalSearchResponse(**result)

    except Exception as e:
        logger.error("Multimodal search failed", error=str(e), query=request.query[:50])
        raise HTTPException(
            status_code=500,
            detail=f"Multimodal search failed: {str(e)}"
        )
