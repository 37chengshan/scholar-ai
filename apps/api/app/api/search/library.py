"""Library search endpoints - internal paper search and fusion.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
Library domain for user's uploaded papers search.

Endpoints:
- GET /library - Search within user's library (Milvus vector search)
- GET /unified - Merge external search results from arXiv + Semantic Scholar
- POST /fusion - Fusion search across library + external sources
"""

import asyncio
import copy
import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, Query

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
from app.deps import CurrentUserId, get_db
from app.middleware.auth import get_optional_user
from app.services.paper_service import PaperService
from app.services.search_library_status_service import (
    search_library_status_service,
)
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


def _stable_query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def _normalize_source_filter(source: Optional[str]) -> str:
    if source is not None and not isinstance(source, str):
        default_value = getattr(source, "default", None)
        return _normalize_source_filter(default_value)
    if not source or source == "all":
        return "all"
    if source in {"s2", "semantic-scholar"}:
        return "semantic_scholar"
    if source in {"internal", "arxiv", "semantic_scholar"}:
        return source
    raise HTTPException(status_code=422, detail=Errors.validation("Invalid source filter"))


def _serialize_search_results(results: List[Any]) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, SearchResult):
            serialized.append(result.model_dump())
        else:
            serialized.append(dict(result))
    return serialized


def _build_internal_search_results(
    papers_payload: Dict[str, Any],
) -> List[SearchResult]:
    task_map = papers_payload.get("task_map", {})
    chunk_count_map = papers_payload.get("chunk_count_map", {})
    internal_results: List[SearchResult] = []

    for paper in papers_payload.get("papers", []):
        chunk_count = int(chunk_count_map.get(paper.id, 0) or 0)
        task = task_map.get(paper.id)
        is_ready = chunk_count > 0 and (
            getattr(task, "status", None) == "completed"
            or getattr(paper, "status", None) == "completed"
        )
        internal_results.append(
            SearchResult(
                id=str(paper.id),
                title=str(paper.title or "Untitled"),
                authors=list(getattr(paper, "authors", []) or []),
                year=getattr(paper, "year", None) or 0,
                abstract=getattr(paper, "abstract", None) or "",
                source="internal",
                url=f"/read/{paper.id}",
                pdfUrl=getattr(paper, "pdf_url", None),
                citationCount=getattr(paper, "citations", None),
                arxivId=getattr(paper, "arxiv_id", None),
                s2PaperId=getattr(paper, "s2_paper_id", None),
                doi=getattr(paper, "doi", None),
                venue=getattr(paper, "venue", None),
                openAccess=bool(getattr(paper, "pdf_url", None)),
                fieldsOfStudy=[],
                availability="pdf_available"
                if getattr(paper, "pdf_url", None)
                else "metadata_only",
                libraryStatus=(
                    "imported_fulltext_ready"
                    if is_ready
                    else "imported_metadata_only"
                ),
                in_library=True,
            )
        )

    return internal_results


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
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    logger.info(
        "search_started",
        event_type="search_started",
        run_id=run_id,
        route="/api/v1/search/library",
        query_hash=_stable_query_hash(q),
        paper_count=len(paper_ids),
    )

    logger.info(
        "Library search initiated",
        query=q[:50],
        paper_count=len(paper_ids),
        user_id=user_id,
    )

    if not paper_ids:
        logger.warning("No paper_ids provided for library search")
        logger.info(
            "search_completed",
            event_type="search_completed",
            run_id=run_id,
            route="/api/v1/search/library",
            result_count=0,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
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
                    content=(
                        r.get("text")
                        or r.get("content")
                        or ""
                    )[:500],
                    section=r.get("section"),
                    page=r.get("page_num"),
                    rrf_score=r.get(
                        "rrf_score",
                        r.get("hybrid_score", r.get("score", r.get("distance", 0.0))),
                    ),
                    dense_score=r.get("score", r.get("distance", 0.0)),
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
        logger.info(
            "search_completed",
            event_type="search_completed",
            run_id=run_id,
            route="/api/v1/search/library",
            result_count=len(library_results),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
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
        logger.error(
            "search_failed",
            event_type="search_failed",
            run_id=run_id,
            route="/api/v1/search/library",
            error=str(e),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
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
    source: Optional[str] = Query(default="all"),
    db: AsyncSession = Depends(get_db),
    optional_user=Depends(get_optional_user),
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
    2. Merged and deduplicated (by arXiv ID + title overlap score)
    3. Filtered by year range
    4. Sorted by citation-based composite score
    """
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    logger.info(
        "search_started",
        event_type="search_started",
        run_id=run_id,
        route="/api/v1/search/unified",
        query_hash=_stable_query_hash(query),
        limit=limit,
        offset=offset,
        year_from=year_from,
        year_to=year_to,
        source=source,
    )

    normalized_source = _normalize_source_filter(source)

    user_scope = getattr(optional_user, "id", "anon")
    cache_key = (
        f"search:unified:{user_scope}:{normalized_source}:{query}:{limit}:{offset}:{year_from}:{year_to}"
    )

    response_meta = {
        "limit": limit,
        "offset": offset,
        "total": 0,
    }

    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Unified search cache hit", query=query, limit=limit)
        cached_data = copy.deepcopy(cached)
        cached_data["results"] = await search_library_status_service.annotate_results(
            cached_data.get("results", []),
            user=optional_user,
            db=db,
        )
        logger.info(
            "search_completed",
            event_type="search_completed",
            run_id=run_id,
            route="/api/v1/search/unified",
            result_count=len(cached_data.get("results", [])),
            cache_hit=True,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        response_meta["total"] = int(cached_data.get("total", len(cached_data.get("results", []))) or 0)
        return SearchResponse(success=True, data=cached_data, meta=response_meta)

    logger.info(
        "Unified search initiated",
        query=query,
        limit=limit,
        year_from=year_from,
        year_to=year_to,
    )

    internal_results: List[SearchResult] = []
    internal_total = 0
    if optional_user is not None and normalized_source in {"all", "internal"}:
        internal_payload = await PaperService.search_papers_for_api(
            db,
            optional_user.id,
            query_text=query,
            page=1,
            limit=limit,
        )
        internal_results = _build_internal_search_results(internal_payload)
        internal_total = int(internal_payload.get("total", len(internal_results)) or 0)

    tasks: List[Any] = []
    task_labels: List[str] = []
    if normalized_source in {"all", "arxiv"}:
        tasks.append(search_arxiv(query, limit=limit, offset=offset))
        task_labels.append("arxiv")
    if normalized_source in {"all", "semantic_scholar"}:
        tasks.append(search_semantic_scholar(query, limit=limit, offset=offset))
        task_labels.append("semantic_scholar")

    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []

    arxiv_list: List[SearchResult] = []
    s2_list: List[SearchResult] = []
    arxiv_total = 0
    s2_total = 0

    for label, result in zip(task_labels, results):
        if isinstance(result, Exception):
            logger.warning(f"{label} search failed: {result}")
            continue

        source_data = result.data if hasattr(result, "data") else result
        if label == "arxiv":
            arxiv_list = source_data.get("results", [])
            arxiv_total = source_data.get("total", 0)
        elif label == "semantic_scholar":
            s2_list = source_data.get("results", [])
            s2_total = source_data.get("total", 0)

    all_results = internal_results + arxiv_list + s2_list
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

    total = len(unique_results)
    response_meta["total"] = total
    paged_results = scored_results[offset : offset + limit]
    cached_result_data = {
        "query": query,
        "source": normalized_source,
        "results": _serialize_search_results(paged_results),
        "total": total,
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
        },
    }

    await set_search_cache(cache_key, cached_result_data)
    response_data = copy.deepcopy(cached_result_data)
    response_data["results"] = await search_library_status_service.annotate_results(
        response_data.get("results", []),
        user=optional_user,
        db=db,
    )
    logger.info(
        "Unified search complete",
        query=query,
        total_results=len(all_results),
        unique_results=len(unique_results),
        returned_results=len(response_data["results"]),
    )
    logger.info(
        "search_completed",
        event_type="search_completed",
        run_id=run_id,
        route="/api/v1/search/unified",
        result_count=len(response_data["results"]),
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )

    return SearchResponse(success=True, data=response_data, meta=response_meta)


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
                    abstract=(
                        r.get("text")
                        or r.get("content")
                        or ""
                    )[:500],
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
