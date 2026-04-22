"""Trace helpers for retrieval pipeline observability."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4


class RetrievalTraceService:
    """Build stable retrieval trace payloads when enabled."""

    def __init__(self, *, enabled: bool = False):
        self.enabled = enabled

    def build_trace(
        self,
        *,
        query: str,
        planner_queries: List[str],
        metadata_filters: Dict[str, Any],
        weights: Dict[str, float],
        results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        trace_id = str(uuid4())
        traced_results = []
        for result in results:
            result["retrieval_trace_id"] = trace_id
            traced_results.append(
                {
                    "paper_id": result.get("paper_id"),
                    "source_id": result.get("source_id"),
                    "backend": result.get("backend", "milvus"),
                    "content_type": result.get("content_type", "text"),
                    "vector_score": result.get("vector_score"),
                    "sparse_score": result.get("sparse_score"),
                    "hybrid_score": result.get("hybrid_score"),
                    "reranker_score": result.get("reranker_score"),
                }
            )

        return {
            "trace_id": trace_id,
            "query": query,
            "planner_queries": planner_queries,
            "metadata_filters": metadata_filters,
            "weights": weights,
            "results": traced_results,
        }