"""Tests for Qdrant filter compilation."""

from app.core.qdrant_filter_compiler import QdrantFilterCompiler
from app.models.retrieval import SearchConstraints


def test_qdrant_filter_compiler_omits_missing_year_bounds():
    compiler = QdrantFilterCompiler()

    from_only = compiler.compile(
        SearchConstraints(user_id="user-1", paper_ids=["paper-1"], year_from=2020)
    )
    to_only = compiler.compile(
        SearchConstraints(user_id="user-1", paper_ids=["paper-1"], year_to=2022)
    )

    from_year_clause = next(item for item in from_only["must"] if item.get("key") == "year")
    to_year_clause = next(item for item in to_only["must"] if item.get("key") == "year")

    assert from_year_clause["range"] == {"gte": 2020}
    assert to_year_clause["range"] == {"lte": 2022}