from __future__ import annotations

from app.core.dashscope_runtime import DashScopeEmbeddingProvider, DashScopeRerankService
from app.rag_v3.rerank.qwen3vl_rerank_adapter import get_rerank_runtime_binding, rerank_candidates
from app.rag_v3.schemas import EvidenceCandidate


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, *, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(self._payload)


def test_dashscope_embedding_provider_parses_embeddings(monkeypatch):
    fake_client = _FakeClient(
        {
            "output": {
                "embeddings": [
                    {"text_index": 0, "embedding": [0.1, 0.2]},
                    {"text_index": 1, "embedding": [0.3, 0.4]},
                ]
            }
        }
    )
    monkeypatch.setattr("app.core.dashscope_runtime.httpx.Client", lambda timeout=None: fake_client)
    monkeypatch.setattr("app.core.dashscope_runtime.settings.DASHSCOPE_API_KEY", "test-key")

    provider = DashScopeEmbeddingProvider(model="text-embedding-v4")
    vectors = provider.embed_texts(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert fake_client.calls[0]["json"]["model"] == "text-embedding-v4"
    assert provider.get_runtime_binding().resolved_mode == "online"


def test_dashscope_rerank_service_parses_results(monkeypatch):
    fake_client = _FakeClient(
        {
            "output": {
                "results": [
                    {"index": 1, "relevance_score": 0.95},
                    {"index": 0, "relevance_score": 0.75},
                ]
            }
        }
    )
    monkeypatch.setattr("app.core.dashscope_runtime.httpx.Client", lambda timeout=None: fake_client)
    monkeypatch.setattr("app.core.dashscope_runtime.settings.DASHSCOPE_API_KEY", "test-key")

    service = DashScopeRerankService(model="qwen3-rerank")
    results = service.rerank(query="q", documents=["d0", "d1"], top_n=2)

    assert results[0]["index"] == 1
    assert results[0]["score"] == 0.95
    assert service.get_runtime_binding().resolved_mode == "online"


def test_rerank_candidates_falls_back_to_deterministic_without_dashscope(monkeypatch):
    monkeypatch.setattr(
        "app.rag_v3.rerank.qwen3vl_rerank_adapter.dashscope_is_configured",
        lambda: False,
    )
    candidates = [
        EvidenceCandidate(source_chunk_id="2", paper_id="p", anchor_text="b", rrf_score=0.2),
        EvidenceCandidate(source_chunk_id="1", paper_id="p", anchor_text="a", rrf_score=0.9),
    ]

    ranked = rerank_candidates(query="q", candidates=candidates)

    assert [item.source_chunk_id for item in ranked] == ["1", "2"]
    assert get_rerank_runtime_binding().resolved_mode == "shim"
