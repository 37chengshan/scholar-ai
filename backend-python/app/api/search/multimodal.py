"""Multimodal search endpoint - text, images, tables with clustering.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
Multimodal domain for cross-modality paper search.

Endpoints:
- POST /multimodal - Search across text, image, and table content
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.page_clustering import cluster_pages
from app.core.auth import CurrentUserId
from app.utils.logger import logger
from app.utils.problem_detail import Errors


router = APIRouter()


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
        service = get_multimodal_search_service()

        result = await service.search(
            query=request.query,
            paper_ids=request.paper_ids,
            user_id=user_id,
            top_k=request.top_k,
            use_reranker=request.use_reranker,
            content_types=request.content_types,
        )

        if request.enable_clustering and result["results"]:
            try:
                clusters = cluster_pages(result["results"])

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


__all__ = [
    "router",
    "multimodal_search",
    "MultimodalSearchRequest",
    "MultimodalSearchResponse",
]
