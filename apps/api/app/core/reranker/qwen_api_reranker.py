"""Qwen API reranker adapter for official runtime."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from app.config import settings
from app.core.model_gateway.active_providers import Qwen3VLRerankProvider
from app.core.reranker.base import BaseRerankerService


class QwenApiRerankerService(BaseRerankerService):
    """Reranker adapter backed by qwen_api provider contract."""

    def __init__(self):
        self._provider = Qwen3VLRerankProvider()
        self._loaded = False

    def load_model(self) -> None:
        self._loaded = True

    def rerank(
        self,
        query: Union[str, Dict[str, Any]],
        documents: List[Union[str, Dict[str, Any]]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self._loaded:
            self.load_model()

        query_text = query if isinstance(query, str) else str(query.get("text") or "")
        texts = [doc if isinstance(doc, str) else str(doc.get("text") or "") for doc in documents]
        ranked = self._provider.rerank(query_text, texts, top_k=top_k)

        results: List[Dict[str, Any]] = []
        for row in ranked:
            index = int(row.get("index", 0))
            if 0 <= index < len(documents):
                original_doc = documents[index]
            else:
                original_doc = row.get("text", "")
            results.append(
                {
                    "document": original_doc,
                    "score": float(row.get("score", 0.0)),
                    "rank": len(results),
                }
            )
        return results

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_info(self) -> Dict[str, str]:
        return {
            "name": settings.RERANKER_MODEL,
            "version": "api",
            "type": "multimodal",
        }

    def supports_multimodal(self) -> bool:
        return True
