"""Local baseline provider wrappers for v2.3.

These wrappers keep local qwen_v2 as baseline/fallback while still using the
same gateway interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
from app.core.model_gateway.base import EmbeddingProvider
from app.core.model_gateway.errors import ProviderBadResponse


class LocalQwenEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "qwen3-vl-2b"):
        self._model_name = model_name
        self._service = Qwen3VLEmbeddingService()
        self._service.load_model()

    def name(self) -> str:
        return "local_qwen"

    def model_name(self) -> str:
        return self._model_name

    def dimension(self) -> int:
        return int(getattr(self._service, "dimension", 2048))

    def supports_image(self) -> bool:
        return True

    def embed_texts(self, texts: List[str], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            vec = self._service.encode_text(text)
            vectors.append(vec)
        return vectors

    def embed_multimodal(self, items: List[Dict[str, Any]], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        vectors: List[List[float]] = []
        for item in items:
            if item.get("text"):
                vectors.append(self._service.encode_text(item["text"]))
                continue
            if item.get("image_path"):
                vectors.append(self._service.encode_image(item["image_path"]))
                continue
            raise ProviderBadResponse("Unsupported local multimodal item")
        return vectors
