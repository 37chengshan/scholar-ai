from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings
from app.core.runtime_contract import RuntimeBinding, build_online_binding, normalize_runtime_mode


_EMBEDDING_ENDPOINT = "/services/embeddings/text-embedding/text-embedding"
_RERANK_ENDPOINT = "/services/rerank/text-rerank/text-rerank"


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def dashscope_api_key() -> str:
    return str(getattr(settings, "DASHSCOPE_API_KEY", "") or "").strip()


def dashscope_is_configured() -> bool:
    return bool(dashscope_api_key())


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {dashscope_api_key()}",
        "Content-Type": "application/json",
    }


def _parse_embedding_payload(payload: dict[str, Any]) -> list[list[float]]:
    output = payload.get("output") if isinstance(payload, dict) else None
    embeddings = []
    if isinstance(output, dict):
        embeddings = output.get("embeddings") or []
    if not embeddings and isinstance(payload.get("data"), list):
        embeddings = payload["data"]

    vectors: list[list[float]] = []
    for item in embeddings:
        vector = item.get("embedding") if isinstance(item, dict) else None
        if isinstance(vector, list):
            vectors.append([float(value) for value in vector])
    if not vectors:
        raise RuntimeError("DashScope embedding response missing embeddings")
    return vectors


def _parse_rerank_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = payload.get("output") if isinstance(payload, dict) else None
    results = []
    if isinstance(output, dict):
        results = output.get("results") or []
    if not results and isinstance(payload.get("results"), list):
        results = payload["results"]
    parsed: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        parsed.append(
            {
                "index": int(item.get("index", 0)),
                "score": float(item.get("relevance_score", item.get("score", 0.0))),
            }
        )
    if not parsed:
        raise RuntimeError("DashScope rerank response missing results")
    return parsed


@dataclass
class DashScopeEmbeddingProvider:
    model: str
    provider_name: str = "dashscope_qwen"
    dimension: int = 1024
    supports_multimodal: bool = False
    _resolved_mode: str = "online"
    _degraded_conditions: list[str] = field(default_factory=list)

    def embed_texts(self, texts: list[str], timeout_s: float | None = None) -> list[list[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": {"texts": texts},
            "parameters": {
                "dimension": self.dimension,
                "text_type": "document",
            },
        }
        try:
            with httpx.Client(timeout=timeout_s or settings.DASHSCOPE_TIMEOUT_SECONDS) as client:
                response = client.post(
                    _join_url(settings.DASHSCOPE_BASE_URL, _EMBEDDING_ENDPOINT),
                    headers=_headers(),
                    json=payload,
                )
                response.raise_for_status()
            self._resolved_mode = "online"
            return _parse_embedding_payload(response.json())
        except Exception as exc:
            self._resolved_mode = "shim"
            message = f"embedding online request failed for {self.model}: {exc}"
            if message not in self._degraded_conditions:
                self._degraded_conditions.append(message)
            raise

    def get_runtime_binding(self) -> RuntimeBinding:
        if self._resolved_mode == "online":
            return build_online_binding(
                component="embedding",
                provider_name=self.provider_name,
                model=self.model,
                dimension=self.dimension,
                supports_multimodal=self.supports_multimodal,
            )
        return RuntimeBinding(
            component="embedding",
            requested_mode=normalize_runtime_mode(),
            resolved_mode="shim",
            provider_name=self.provider_name,
            provider_kind="api_provider",
            model=self.model,
            dimension=self.dimension,
            supports_multimodal=self.supports_multimodal,
            degraded_conditions=tuple(self._degraded_conditions),
        )


@dataclass
class DashScopeRerankService:
    model: str
    provider_name: str = "dashscope_qwen"
    _resolved_mode: str = "online"
    _degraded_conditions: list[str] = field(default_factory=list)

    def rerank(self, *, query: str, documents: list[str], top_n: int | None = None) -> list[dict[str, Any]]:
        if not documents:
            return []

        payload = {
            "model": self.model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": top_n or len(documents),
            },
        }
        try:
            with httpx.Client(timeout=settings.DASHSCOPE_TIMEOUT_SECONDS) as client:
                response = client.post(
                    _join_url(settings.DASHSCOPE_BASE_URL, _RERANK_ENDPOINT),
                    headers=_headers(),
                    json=payload,
                )
                response.raise_for_status()
            self._resolved_mode = "online"
            return _parse_rerank_payload(response.json())
        except Exception as exc:
            self._resolved_mode = "shim"
            message = f"rerank online request failed for {self.model}: {exc}"
            if message not in self._degraded_conditions:
                self._degraded_conditions.append(message)
            raise

    def get_runtime_binding(self) -> RuntimeBinding:
        if self._resolved_mode == "online":
            return build_online_binding(
                component="reranker",
                provider_name=self.provider_name,
                model=self.model,
                dimension=None,
                supports_multimodal=False,
            )
        return RuntimeBinding(
            component="reranker",
            requested_mode=normalize_runtime_mode(),
            resolved_mode="shim",
            provider_name=self.provider_name,
            provider_kind="api_provider",
            model=self.model,
            dimension=None,
            supports_multimodal=False,
            degraded_conditions=tuple(self._degraded_conditions),
        )
