"""Semantic Scholar API endpoints.

Provides REST endpoints for SemanticScholarService methods.
"""

from fastapi import APIRouter, Depends, Query, Body
from typing import List, Optional, Dict, Any

from app.core.semantic_scholar_service import get_semantic_scholar_service
from app.core.redis_client import get_redis_client

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