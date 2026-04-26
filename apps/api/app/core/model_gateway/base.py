"""Model Gateway provider interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ProviderMetrics:
    provider: str
    model_name: str
    request_count: int
    total_latency_ms: float
    estimated_cost: float


class EmbeddingProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def supports_image(self) -> bool:
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_multimodal(self, items: List[Dict[str, Any]], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        pass


class RerankProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def rerank(self, query: str, documents: List[str], *, top_k: int) -> List[Dict[str, Any]]:
        pass


class LLMProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        pass


class VLMProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, text: str, image_b64: str, *, max_tokens: int = 512) -> str:
        pass
