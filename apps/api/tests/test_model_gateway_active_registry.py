"""Tests for active model gateway provider registry."""

from __future__ import annotations

from app.core.model_gateway.registry import (
    get_active_provider_registry,
    get_embedding_provider,
    get_llm_provider,
    get_reranker_provider,
)


def test_active_registry_returns_only_official_providers():
    embedding_cls = get_embedding_provider()
    reranker_cls = get_reranker_provider()
    llm_cls = get_llm_provider()

    assert embedding_cls.__name__ == "TongyiVisionFlashEmbeddingProvider"
    assert reranker_cls.__name__ == "Qwen3VLRerankProvider"
    assert llm_cls.__name__ == "GLM45AirProvider"

    registry = get_active_provider_registry()
    assert set(registry.keys()) == {"embedding", "reranker", "llm"}
