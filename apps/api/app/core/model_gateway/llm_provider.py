"""LLM provider placeholders for v2.3 gateway."""

from __future__ import annotations

from app.core.model_gateway.base import LLMProvider


class NoopLLMProvider(LLMProvider):
    def __init__(self, name: str = "noop", model_name: str = "noop-llm"):
        self._name = name
        self._model_name = model_name

    def name(self) -> str:
        return self._name

    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        return "[noop-llm] generation disabled in probe mode"
