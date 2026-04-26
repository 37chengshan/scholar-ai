"""Provider registry for v2.3 model gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Type

from app.core.model_gateway.base import EmbeddingProvider, LLMProvider, RerankProvider, VLMProvider
from app.core.model_gateway.active_providers import (
    GLM45AirProvider,
    Qwen3VLRerankProvider,
    TongyiVisionFlashEmbeddingProvider,
)
from app.core.model_gateway.errors import ProviderBadResponse


@dataclass
class ProviderRegistry:
    embedding: Dict[str, EmbeddingProvider]
    rerank: Dict[str, RerankProvider]
    llm: Dict[str, LLMProvider]
    vlm: Dict[str, VLMProvider]

    def get_embedding(self, key: str) -> EmbeddingProvider:
        provider = self.embedding.get(key)
        if provider is None:
            raise ProviderBadResponse(f"Unknown embedding provider: {key}")
        return provider

    def get_rerank(self, key: str) -> RerankProvider:
        provider = self.rerank.get(key)
        if provider is None:
            raise ProviderBadResponse(f"Unknown rerank provider: {key}")
        return provider

    def get_llm(self, key: str) -> LLMProvider:
        provider = self.llm.get(key)
        if provider is None:
            raise ProviderBadResponse(f"Unknown llm provider: {key}")
        return provider

    def get_vlm(self, key: str) -> VLMProvider:
        provider = self.vlm.get(key)
        if provider is None:
            raise ProviderBadResponse(f"Unknown vlm provider: {key}")
        return provider


_registry: Optional[ProviderRegistry] = None


ACTIVE_PROVIDER_REGISTRY = {
    "embedding": TongyiVisionFlashEmbeddingProvider,
    "reranker": Qwen3VLRerankProvider,
    "llm": GLM45AirProvider,
}


def set_registry(registry: ProviderRegistry) -> None:
    global _registry
    _registry = registry


def get_registry() -> ProviderRegistry:
    if _registry is None:
        raise ProviderBadResponse("Provider registry has not been initialized")
    return _registry


def get_embedding_provider() -> Type[EmbeddingProvider]:
    return ACTIVE_PROVIDER_REGISTRY["embedding"]


def get_reranker_provider() -> Type[RerankProvider]:
    return ACTIVE_PROVIDER_REGISTRY["reranker"]


def get_llm_provider() -> Type[LLMProvider]:
    return ACTIVE_PROVIDER_REGISTRY["llm"]


def get_active_provider_registry() -> dict[str, type]:
    return dict(ACTIVE_PROVIDER_REGISTRY)
