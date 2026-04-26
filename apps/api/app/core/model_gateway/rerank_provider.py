"""Rerank provider placeholders for v2.3 gateway."""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.model_gateway.base import RerankProvider


class NoopRerankProvider(RerankProvider):
    def __init__(self, name: str = "noop", model_name: str = "noop-reranker"):
        self._name = name
        self._model_name = model_name

    def name(self) -> str:
        return self._name

    def model_name(self) -> str:
        return self._model_name

    def rerank(self, query: str, documents: List[str], *, top_k: int) -> List[Dict[str, Any]]:
        sliced = documents[:top_k]
        return [{"index": i, "score": float(len(sliced) - i), "text": doc} for i, doc in enumerate(sliced)]
