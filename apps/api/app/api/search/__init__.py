"""Search single-entry module.

Provides one canonical import path:
`from app.api.search import ...`
"""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rag_v3.main_path_service import build_answer_contract_payload

from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.page_clustering import cluster_pages

from .external import (
	resolve_doi,
	router as external_router,
	search_arxiv as _search_arxiv_endpoint,
	search_semantic_scholar as _search_semantic_scholar_endpoint,
)
from .library import (
	fusion_search,
	router as library_router,
	search_library,
)
from .multimodal import (
	MultimodalSearchRequest,
	MultimodalSearchResponse,
	multimodal_search,
	router as multimodal_router,
)
from .shared import (
	FusionSearchRequest,
	FusionSearchResponse,
	LibrarySearchResponse,
	LibrarySearchResult,
	RateLimiter,
	SearchResponse,
	SearchResult,
	_arxiv_rate_limiter,
	_s2_rate_limiter,
	calculate_paper_score,
	deduplicate_results,
	get_search_cache,
	get_redis_client,
	set_search_cache,
)


router = APIRouter()
router.include_router(external_router)
router.include_router(library_router)
router.include_router(multimodal_router)


class V3SearchRequest(BaseModel):
	query: str = Field(..., min_length=1)
	query_family: str = "fact"
	top_k: int = Field(default=10, ge=1, le=50)
	paper_id: str | None = None
	section_paths: list[str] | None = None
	page_from: int | None = None
	page_to: int | None = None
	content_types: list[str] | None = None


@router.post("/evidence")
async def search_evidence_v3(request: V3SearchRequest):
	try:
		payload = build_answer_contract_payload(
			query=request.query,
			user_id="search-system",
			paper_scope=[request.paper_id] if request.paper_id else None,
			query_family=request.query_family,
			stage="rule",
			top_k=request.top_k,
			section_paths=request.section_paths,
			page_from=request.page_from,
			page_to=request.page_to,
			content_types=request.content_types,
		)

		citations = payload.get("citations", [])[: request.top_k]
		evidence = payload.get("evidence_blocks", [])[: request.top_k]
		papers = sorted({c.get("paper_id") for c in citations if c.get("paper_id")})
		sections = sorted({c.get("section_path") for c in citations if c.get("section_path")})

		return {
			"paper_results": papers,
			"section_matches": sections,
			"evidence_matches": evidence,
			"relation_matches": [],
			"answer_mode": payload.get("answer_mode"),
			"retrieval_trace_id": payload.get("retrieval_trace_id") or payload.get("trace_id"),
			"quality": payload.get("quality", {}),
		}
	except Exception as exc:
		return {
			"paper_results": [],
			"section_matches": [],
			"evidence_matches": [],
			"relation_matches": [],
			"answer_mode": "abstain",
			"retrieval_trace_id": None,
			"quality": {
				"error": "search_evidence_unavailable",
				"message": str(exc),
			},
		}


def _extract_data(result: Any) -> Dict[str, Any]:
	"""Normalize endpoint/search return payload to legacy dict shape."""
	if isinstance(result, dict):
		if "data" in result and isinstance(result.get("data"), dict):
			return result["data"]
		return result
	return getattr(result, "data", {}) or {}


async def search_arxiv(
	query: str,
	limit: int = 20,
	offset: int = 0,
) -> Dict[str, Any]:
	"""Compatibility wrapper for direct function imports.

	Returns legacy dict payload instead of Pydantic envelope object.
	"""
	result = await _search_arxiv_endpoint(query=query, limit=limit, offset=offset)
	return _extract_data(result)


async def search_semantic_scholar(
	query: str,
	limit: int = 20,
	offset: int = 0,
) -> Dict[str, Any]:
	"""Compatibility wrapper for direct function imports."""
	result = await _search_semantic_scholar_endpoint(
		query=query,
		limit=limit,
		offset=offset,
	)
	return _extract_data(result)


async def search_unified(
	query: str,
	limit: int = 20,
	offset: int = 0,
	year_from: Optional[int] = None,
	year_to: Optional[int] = None,
) -> Dict[str, Any]:
	"""Legacy unified search function for direct imports and unit tests."""
	arxiv_task = search_arxiv(query=query, limit=limit, offset=offset)
	s2_task = search_semantic_scholar(query=query, limit=limit, offset=offset)
	results = await asyncio.gather(arxiv_task, s2_task, return_exceptions=True)

	arxiv_list = []
	s2_list = []

	if not isinstance(results[0], Exception):
		arxiv_list = _extract_data(results[0]).get("results", [])
	if not isinstance(results[1], Exception):
		s2_list = _extract_data(results[1]).get("results", [])

	merged = deduplicate_results(arxiv_list + s2_list)

	if year_from is not None:
		merged = [r for r in merged if r.year >= year_from]
	if year_to is not None:
		merged = [r for r in merged if r.year <= year_to]

	ranked = sorted(
		merged,
		key=lambda r: calculate_paper_score(
			getattr(r, "citationCount", None),
			r.year,
			relevance=0.5,
		),
		reverse=True,
	)

	return {
		"results": ranked[:limit],
		"total": len(ranked),
	}


__all__ = [
	"router",
	"RateLimiter",
	"SearchResult",
	"SearchResponse",
	"LibrarySearchResult",
	"LibrarySearchResponse",
	"FusionSearchRequest",
	"FusionSearchResponse",
	"_arxiv_rate_limiter",
	"_s2_rate_limiter",
	"get_redis_client",
	"get_search_cache",
	"set_search_cache",
	"calculate_paper_score",
	"deduplicate_results",
	"search_arxiv",
	"search_semantic_scholar",
	"resolve_doi",
	"search_library",
	"search_unified",
	"fusion_search",
	"multimodal_search",
	"MultimodalSearchRequest",
	"MultimodalSearchResponse",
	"get_multimodal_search_service",
	"cluster_pages",
]
