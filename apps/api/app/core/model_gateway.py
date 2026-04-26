from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass
class _DeterministicEmbeddingProvider:
    model: str
    dim: int = 1024

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


def create_embedding_provider(provider: str, model: str):
    """Compatibility gateway used by evaluation scripts.

    The original API-based embedding gateway is not available in this repository snapshot.
    This compatibility shim keeps benchmark/retrieval scripts executable by providing a
    deterministic local embedding implementation with stable dimensions.
    """
    _ = provider
    return _DeterministicEmbeddingProvider(model=model)
