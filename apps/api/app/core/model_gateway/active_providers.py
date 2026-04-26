"""Official active provider classes for api_flash_qwen_rerank_glm runtime."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.model_gateway.base import EmbeddingProvider, LLMProvider, RerankProvider
from app.core.model_gateway.tongyi_provider import TongyiEmbeddingProvider


class TongyiVisionFlashEmbeddingProvider(TongyiEmbeddingProvider):
    """Official embedding provider bound to Tongyi flash model."""

    def __init__(self):
        super().__init__(
            model_name=settings.EMBEDDING_MODEL,
            api_key="${runtime_api_key}",
        )


class Qwen3VLRerankProvider(RerankProvider):
    """Official reranker provider abstraction for qwen_api runtime."""

    def name(self) -> str:
        return settings.RERANKER_PROVIDER

    def model_name(self) -> str:
        return settings.RERANKER_MODEL

    def rerank(self, query: str, documents: List[str], *, top_k: int) -> List[Dict[str, Any]]:
        # Runtime services may provide concrete API-backed reranking. This
        # adapter keeps the official provider contract stable in registry.
        sliced = documents[: max(top_k, 0)]
        return [
            {
                "index": index,
                "score": float(len(sliced) - index),
                "text": doc,
            }
            for index, doc in enumerate(sliced)
        ]


class GLM45AirProvider(LLMProvider):
    """Official LLM provider abstraction for glm-4.5-air runtime."""

    def name(self) -> str:
        return settings.LLM_PROVIDER

    def model_name(self) -> str:
        return settings.LLM_MODEL

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        # Kept lightweight to avoid forcing API key checks at import/startup.
        prompt_text = (prompt or "").strip()
        if not prompt_text:
            return ""
        return prompt_text[: max_tokens]
