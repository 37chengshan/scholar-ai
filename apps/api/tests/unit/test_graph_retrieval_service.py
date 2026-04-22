import pytest

from app.config import settings
from app.core.graph_retrieval_service import GraphRetrievalService


@pytest.mark.asyncio
async def test_graph_retrieval_service_expand_graph_context_for_compare() -> None:
    service = GraphRetrievalService()

    results = await service.expand_graph_context(
        graph_hint={"query_family": "compare", "requires_graph": True},
        paper_ids=["paper-1", "paper-2"],
        query="compare method A and baseline B",
    )

    assert len(results) == 2
    assert all(item["relation"] == "compares_against_baseline" for item in results)


@pytest.mark.asyncio
async def test_graph_retrieval_service_respects_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GraphRetrievalService()
    monkeypatch.setattr(settings, "GRAPH_RETRIEVAL_ENABLED", False)

    results = await service.expand_graph_context(
        graph_hint={"query_family": "compare", "requires_graph": True},
        paper_ids=["paper-1"],
        query="compare method A and baseline B",
    )

    assert results == []
