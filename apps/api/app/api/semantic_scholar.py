"""Semantic Scholar API endpoints.

Provides REST endpoints for SemanticScholarService methods.
"""

from fastapi import APIRouter, Depends, Query, Body
from typing import List, Optional, Dict, Any

from app.core.semantic_scholar_service import get_semantic_scholar_service
from app.core.redis_client import get_redis_client
from app.utils.problem_detail import Errors

router = APIRouter()


@router.post("/batch")
async def batch_get_papers(
    ids: List[str] = Body(..., embed=True),
    fields: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """Batch get papers by IDs.

    Per D-01: Max 1000 IDs.
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.batch_get_papers(ids, fields, redis)


@router.get("/paper/{paper_id}")
async def get_paper_details(
    paper_id: str,
    fields: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get single paper details."""
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.get_paper_details(paper_id, fields, redis)


@router.get("/paper/{paper_id}/citations")
async def get_citations(
    paper_id: str,
    fields: Optional[str] = Query(None),
    limit: int = Query(1000)
) -> List[Dict[str, Any]]:
    """Get citations for a paper (who cited this paper).

    Per D-02: Single depth, paginated.
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.get_citations(paper_id, fields, limit, redis)


@router.get("/paper/{paper_id}/references")
async def get_references(
    paper_id: str,
    fields: Optional[str] = Query(None),
    limit: int = Query(1000)
) -> List[Dict[str, Any]]:
    """Get references for a paper (what this paper cited).

    Per D-02: Single depth, paginated.
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.get_references(paper_id, fields, limit, redis)


@router.get("/autocomplete")
async def autocomplete_papers(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """Paper autocomplete for search box.

    Per D-01: Frontend triggers at >=3 chars
    Per D-03: Default limit 5
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.autocomplete_papers(query, limit, redis)


@router.get("/author/search")
async def search_authors(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Search authors by name.

    Per D-05: Called from Author tab
    Per D-06: Returns hIndex, citationCount, paperCount
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.search_authors(query, None, limit, offset, redis)


@router.get("/author/{author_id}/papers")
async def get_author_papers(
    author_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get papers by author ID.

    Per D-07: Pagination 10 per page
    """
    service = get_semantic_scholar_service()
    redis = await get_redis_client()

    return await service.get_author_papers(author_id, None, limit, offset, redis)