"""Active model gateway registry for the single RAG runtime.

This registry is intentionally metadata-only. Concrete provider clients can bind
against the returned contract without importing deprecated local model code.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.rag_runtime_profile import get_active_rag_runtime_profile


@dataclass(frozen=True)
class ProviderBinding:
    task: str
    provider: str
    model: str


@dataclass(frozen=True)
class ModelGatewayRegistry:
    runtime_profile: str
    embedding: ProviderBinding
    reranker: ProviderBinding
    llm: ProviderBinding

    def active_provider_values(self) -> list[str]:
        return [
            self.runtime_profile,
            self.embedding.provider,
            self.embedding.model,
            self.reranker.provider,
            self.reranker.model,
            self.llm.provider,
            self.llm.model,
        ]


def get_active_model_gateway_registry() -> ModelGatewayRegistry:
    profile = get_active_rag_runtime_profile()
    return ModelGatewayRegistry(
        runtime_profile=profile.name,
        embedding=ProviderBinding(
            task="embedding",
            provider=profile.embedding_provider,
            model=profile.embedding_model,
        ),
        reranker=ProviderBinding(
            task="rerank",
            provider=profile.reranker_provider,
            model=profile.reranker_model,
        ),
        llm=ProviderBinding(
            task="llm",
            provider=profile.llm_provider,
            model=profile.llm_model,
        ),
    )
