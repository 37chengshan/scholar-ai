"""Embedding provider factory bootstrap for v2.3."""

from __future__ import annotations

import os

from app.core.model_gateway.base import EmbeddingProvider
from app.core.model_gateway.errors import ProviderAuthError
from app.core.model_gateway.local_provider import LocalQwenEmbeddingProvider
from app.core.model_gateway.tongyi_provider import TongyiEmbeddingProvider


def create_embedding_provider(provider: str, model_name: str) -> EmbeddingProvider:
    if provider == "tongyi":
        api_key = os.getenv("TONGYI_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or ""
        if not api_key:
            raise ProviderAuthError("TONGYI_API_KEY/DASHSCOPE_API_KEY is required for tongyi provider")
        return TongyiEmbeddingProvider(model_name=model_name, api_key=api_key)

    if provider == "local_qwen":
        return LocalQwenEmbeddingProvider(model_name=model_name)

    raise ProviderAuthError(f"Unknown embedding provider: {provider}")
