"""Compile SearchConstraints into a backend-neutral Qdrant filter payload."""

from __future__ import annotations

from typing import Any, Dict, List

from app.models.retrieval import SearchConstraints


class QdrantFilterCompiler:
    """Translate retrieval constraints into a simple Qdrant filter structure."""

    def compile(self, constraints: SearchConstraints) -> Dict[str, List[Dict[str, Any]]]:
        must: List[Dict[str, Any]] = []

        must.append({"key": "user_id", "match": {"value": constraints.user_id}})

        if constraints.paper_ids:
            must.append({"key": "paper_id", "match": {"any": constraints.paper_ids}})
        if constraints.section:
            must.append({"key": "section", "match": {"value": constraints.section}})
        if constraints.content_types:
            must.append({"key": "content_type", "match": {"any": constraints.content_types}})
        if constraints.year_from is not None or constraints.year_to is not None:
            year_range: Dict[str, Any] = {}
            if constraints.year_from is not None:
                year_range["gte"] = constraints.year_from
            if constraints.year_to is not None:
                year_range["lte"] = constraints.year_to
            must.append(
                {
                    "key": "year",
                    "range": year_range,
                }
            )
        if constraints.min_quality_score is not None:
            must.append(
                {
                    "key": "quality_score",
                    "range": {"gte": constraints.min_quality_score},
                }
            )

        return {"must": must}