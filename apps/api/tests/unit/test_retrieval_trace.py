"""Unit tests for retrieval trace helpers."""

from app.core.retrieval_trace import RetrievalTraceService


def test_build_trace_attaches_trace_metadata_when_enabled():
    service = RetrievalTraceService(enabled=True)
    results = [
        {
            "paper_id": "paper-1",
            "text": "chunk",
            "backend": "milvus",
            "vector_score": 0.8,
            "sparse_score": 0.2,
            "hybrid_score": 0.65,
            "reranker_score": 0.9,
        }
    ]

    trace = service.build_trace(
        query="transformer attention",
        planner_queries=["transformer attention"],
        metadata_filters={"section": "Methods"},
        weights={"text": 0.7, "image": 0.2, "table": 0.1},
        results=results,
    )

    assert trace is not None
    assert trace["trace_id"]
    assert trace["results"][0]["backend"] == "milvus"
    assert results[0]["retrieval_trace_id"] == trace["trace_id"]


def test_build_trace_returns_none_when_disabled():
    service = RetrievalTraceService(enabled=False)

    trace = service.build_trace(
        query="query",
        planner_queries=["query"],
        metadata_filters={},
        weights={"text": 1.0},
        results=[],
    )

    assert trace is None