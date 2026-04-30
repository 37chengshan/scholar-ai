from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from app.config import settings
from app.core.dashscope_runtime import DashScopeEmbeddingProvider, dashscope_is_configured
from app.core.runtime_contract import RuntimeBinding, build_shim_binding


@dataclass
class _DeterministicEmbeddingProvider:
    model: str
    dim: int = 1024
    provider_name: str = "deterministic_gateway"
    mode: str = "shim"

    def embed_texts(self, texts: list[str], timeout_s: float | None = None) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            seed = int(hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16], 16)
            rnd = random.Random(seed)
            vec = [rnd.uniform(-1.0, 1.0) for _ in range(self.dim)]
            # L2 normalize to keep cosine behavior stable.
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return vectors

    def get_runtime_binding(self) -> RuntimeBinding:
        return build_shim_binding(
            component="embedding",
            provider_name=self.provider_name,
            model=self.model,
            dimension=self.dim,
        )


def create_embedding_provider(provider: str, model: str):
    """Compatibility gateway used by evaluation scripts.

    When DashScope is configured, Phase H prefers the official online embedding
    provider. Otherwise it falls back to a deterministic shim and surfaces that
    degraded condition through runtime truth.
    """
    if dashscope_is_configured():
        resolved_model = model
        if model == "qwen_flash":
            resolved_model = settings.DASHSCOPE_EMBEDDING_MODEL_FLASH
        elif model == "qwen_pro":
            resolved_model = settings.DASHSCOPE_EMBEDDING_MODEL_PRO
        return DashScopeEmbeddingProvider(
            model=resolved_model,
            provider_name=provider or "dashscope_qwen",
            dimension=1024,
        )
    return _DeterministicEmbeddingProvider(model=model, provider_name=provider or "deterministic_gateway")
