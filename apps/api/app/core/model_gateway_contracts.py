"""Provider contracts for the active RAG runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class ProviderProbeResult:
    provider: str
    model: str
    status: str
    dimension: int | None = None
    supports_batch: bool = False
    supports_image: bool = False
    error: str | None = None


@dataclass(frozen=True)
class RerankCandidate:
    source_chunk_id: str
    paper_id: str
    content_data: str
    page_num: int = 0
    section: str = ""
    content_type: str = "text"


@dataclass(frozen=True)
class RerankResult:
    source_chunk_id: str
    score: float
    rank: int


class EmbeddingProvider(Protocol):
    def name(self) -> str: ...
    def model_name(self) -> str: ...
    def dimension(self) -> int: ...
    def supports_image(self) -> bool: ...
    async def probe(self) -> ProviderProbeResult: ...
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class RerankProvider(Protocol):
    def name(self) -> str: ...
    def model_name(self) -> str: ...
    async def probe(self) -> ProviderProbeResult: ...
    async def rerank(self, query: str, candidates: Sequence[RerankCandidate]) -> list[RerankResult]: ...


class LLMProvider(Protocol):
    def name(self) -> str: ...
    def model_name(self) -> str: ...
    async def probe(self) -> ProviderProbeResult: ...
    async def complete(self, prompt: str) -> str: ...
