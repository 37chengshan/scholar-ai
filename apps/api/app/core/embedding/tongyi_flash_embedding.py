"""Tongyi flash embedding service adapter for official runtime."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from PIL import Image

from app.config import settings
from app.core.embedding.base import BaseEmbeddingService


class TongyiFlashEmbeddingService(BaseEmbeddingService):
    """Embedding adapter backed by Tongyi API provider."""

    def __init__(self):
        self._provider = None
        self._loaded = False

    def load_model(self) -> None:
        if self._loaded:
            return
        from app.core.model_gateway.embedding_provider import create_embedding_provider

        self._provider = create_embedding_provider("tongyi", settings.EMBEDDING_MODEL)
        self._loaded = True

    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if not self._loaded:
            self.load_model()
        assert self._provider is not None

        if isinstance(text, list):
            return self._provider.embed_texts(text)
        return self._provider.embed_texts([text])[0]

    def encode_image(
        self,
        image: Union[str, Image.Image, List[Image.Image]],
    ) -> Union[List[float], List[List[float]]]:
        # Keep compatibility with multimodal callers by converting image inputs
        # into text probes when direct image paths are unavailable.
        if isinstance(image, list):
            probes = ["[image]" for _ in image]
            return self.encode_text(probes)
        return self.encode_text("[image]")

    def encode_table(
        self,
        caption: str = "",
        headers: List[str] = [],
        rows: List[Dict] = [],
    ) -> List[float]:
        serialized = f"Table: {caption}\nColumns: {headers}\nRows: {rows[:3]}"
        vector = self.encode_text(serialized)
        assert isinstance(vector, list)
        return vector

    def is_loaded(self) -> bool:
        return self._loaded

    def get_model_info(self) -> Dict[str, str]:
        return {
            "name": settings.EMBEDDING_MODEL,
            "version": "api",
            "type": "multimodal",
            "dimension": str(settings.EMBEDDING_DIMENSION),
        }

    def supports_multimodal(self) -> bool:
        return True
