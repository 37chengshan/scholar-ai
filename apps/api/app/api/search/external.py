"""External search endpoints - arXiv, Semantic Scholar, DOI resolution.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
External integration domain for paper search APIs.

Endpoints:
- GET /arxiv - Search arXiv papers
- GET /semantic-scholar - Search Semantic Scholar papers
- GET /doi/{doi} - Resolve DOI to metadata via CrossRef
"""

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Query

from .shared import (
    _arxiv_rate_limiter,
    _s2_rate_limiter,
    SearchResponse,
    SearchResult,
    get_search_cache,
    set_search_cache,
)
from app.utils.logger import logger


router = APIRouter()


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

    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("arXiv search cache hit", query=query, limit=limit)
        return SearchResponse(success=True, data=cached)

    logger.info("arXiv search cache miss", query=query, limit=limit)

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

            if response.status_code == 429:
                logger.warning("arXiv API rate limited", query=query, status_code=429)
                _arxiv_rate_limiter.record_failure()
                return SearchResponse(success=True, data={"results": [], "total": 0})

            response.raise_for_status()
            _arxiv_rate_limiter.record_success()

        root = ET.fromstring(response.text)

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
            id_url = entry.findtext("atom:id", "", ns)
            arxiv_id = id_url.split("/")[-1] if id_url else ""

            if "v" in arxiv_id:
                arxiv_id = arxiv_id.split("v")[0]

            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name)

            published = entry.findtext("atom:published", "", ns)
            year = int(published[:4]) if published and len(published) >= 4 else 0

            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

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

    cached = await get_search_cache(cache_key)
    if cached:
        logger.info("Semantic Scholar search cache hit", query=query, limit=limit)
        return SearchResponse(success=True, data=cached)

    logger.info("Semantic Scholar search cache miss", query=query, limit=limit)

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
            paper_id = paper.get("paperId", "")

            authors = []
            for author in paper.get("authors", []):
                name = author.get("name")
                if name:
                    authors.append(name)

            open_access = paper.get("openAccessPdf", {}) or {}
            pdf_url = open_access.get("url") if open_access else None

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
    from .shared import get_redis_client

    service = CrossRefService()
    redis_client = await get_redis_client()

    result = await service.resolve_doi(doi, redis_client)
    return {"success": True, "data": result}


__all__ = ["router", "search_arxiv", "search_semantic_scholar", "resolve_doi"]
