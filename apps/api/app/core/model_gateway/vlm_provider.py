"""VLM provider placeholders for v2.3 gateway."""

from __future__ import annotations

from app.core.model_gateway.base import VLMProvider


class NoopVLMProvider(VLMProvider):
    def __init__(self, name: str = "noop", model_name: str = "noop-vlm"):
        self._name = name
        self._model_name = model_name

    def name(self) -> str:
        return self._name

    def model_name(self) -> str:
        return self._model_name

    def analyze(self, text: str, image_b64: str, *, max_tokens: int = 512) -> str:
        return "[noop-vlm] analysis disabled in probe mode"
