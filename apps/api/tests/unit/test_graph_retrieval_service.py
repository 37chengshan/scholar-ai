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


@pytest.mark.asyncio
async def test_graph_retrieval_service_reason_citation_context_returns_structured_expansion() -> None:
    service = GraphRetrievalService()

    report = await service.reason_citation_context(
        query="compare method A and B",
        query_family="compare",
        paper_ids=["paper-1", "paper-2", "paper-3"],
        top_k=6,
    )

    assert "foundational" in report
    assert "follow_up" in report
    assert "competing" in report
    assert "evolution_chain" in report
    assert "merged_candidates" in report
    assert isinstance(report["merged_candidates"], list)
