"""Model Gateway exports."""

from app.core.model_gateway.base import EmbeddingProvider, LLMProvider, RerankProvider, VLMProvider
from app.core.model_gateway.embedding_provider import create_embedding_provider
from app.core.model_gateway.registry import (
    get_active_provider_registry,
    get_embedding_provider,
    get_llm_provider,
    get_reranker_provider,
)
from app.core.model_gateway.errors import (
    ProviderAuthError,
    ProviderBadResponse,
    ProviderDimensionMismatch,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)

__all__ = [
    "EmbeddingProvider",
    "RerankProvider",
    "LLMProvider",
    "VLMProvider",
    "create_embedding_provider",
    "get_embedding_provider",
    "get_reranker_provider",
    "get_llm_provider",
    "get_active_provider_registry",
    "ProviderError",
    "ProviderTimeout",
    "ProviderRateLimited",
    "ProviderDimensionMismatch",
    "ProviderAuthError",
    "ProviderBadResponse",
    "ProviderUnavailable",
]
