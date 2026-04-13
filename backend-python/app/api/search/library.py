"""Library search endpoints - internal paper search and fusion.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
Library domain for user's uploaded papers search.

Endpoints:
- GET /library - Search within user's library (Milvus vector search)
- GET /unified - Merge external search results from arXiv + Semantic Scholar
- POST /fusion - Fusion search across library + external sources
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from .shared import (
    LibrarySearchResponse,
    LibrarySearchResult,
    SearchResponse,
    SearchResult,
    FusionSearchRequest,
    FusionSearchResponse,
    calculate_paper_score,
    deduplicate_results,
    get_search_cache,
    set_search_cache,
)
from .external import search_arxiv, search_semantic_scholar
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.auth import CurrentUserId
from app.utils.logger import logger
from app.utils.problem_detail import Errors


router = APIRouter()


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
        result = await get_multimodal_search_service().search(
            query=q,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=limit,
            use_reranker=True,
        )

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
                    sparse_score=0.0,
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
        arxiv_data = results[0].data if hasattr(results[0], "data") else results[0]
        arxiv_list = arxiv_data.get("results", [])
        arxiv_total = arxiv_data.get("total", 0)

    if isinstance(results[1], Exception):
        logger.warning(f"Semantic Scholar search failed: {results[1]}")
    else:
        s2_data = results[1].data if hasattr(results[1], "data") else results[1]
        s2_list = s2_data.get("results", [])
        s2_total = s2_data.get("total", 0)

    all_results = arxiv_list + s2_list
    unique_results = deduplicate_results(all_results)

    if year_from is not None:
        unique_results = [r for r in unique_results if r.year >= year_from]
    if year_to is not None:
        unique_results = [r for r in unique_results if r.year <= year_to]

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

    tasks = []

    if "library" in request.sources and request.paper_ids:

        async def search_library_internal():
            service = get_multimodal_search_service()
            result = await service.search(
                query=request.query,
                paper_ids=request.paper_ids,
                user_id=user_id,
                top_k=20,
                use_reranker=True,
            )

            library_results = []
            for r in result.get("results", []):
                library_results.append(
                    SearchResult(
                        id=r.get("id", ""),
                        title=r.get("title", "Unknown"),
                        authors=[],
                        year=r.get("year", 0),
                        abstract=r.get("content_data", "")[:500],
                        source="library",
                        url="",
                        pdfUrl=None,
                        citationCount=None,
                        arxivId=None,
                    )
                )
            return library_results

        tasks.append(("library", search_library_internal()))

    if "arxiv" in request.sources:
        tasks.append(("arxiv", search_arxiv(query=request.query, limit=10)))

    if "semantic_scholar" in request.sources:
        tasks.append(
            ("semantic_scholar", search_semantic_scholar(query=request.query, limit=10))
        )

    search_results = await asyncio.gather(
        *[task[1] for task in tasks], return_exceptions=True
    )

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
            if source_name == "library":
                source_results = result
            else:
                if hasattr(result, "data"):
                    source_results = result.data.get("results", [])
                else:
                    source_results = result.get("results", [])

            for r in source_results:
                if source_name != "library":
                    r.in_library = False

            results.extend(source_results)
            sources_status[source_name] = {
                "count": len(source_results),
                "success": True,
            }

    unique_results = deduplicate_results(results)

    scored_results = sorted(
        unique_results,
        key=lambda r: calculate_paper_score(
            r.citationCount,
            r.year,
            relevance=1.0 if r.source == "library" else 0.5,
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


__all__ = ["router", "search_library", "search_unified", "fusion_search"]
