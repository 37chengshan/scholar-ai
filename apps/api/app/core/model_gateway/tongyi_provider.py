"""Tongyi provider implementations for API-first v2.3."""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.core.model_gateway.base import EmbeddingProvider
from app.core.model_gateway.errors import (
    ProviderAuthError,
    ProviderBadResponse,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.utils.logger import logger


class TongyiEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embedding provider wrapper for Tongyi-style endpoints.

    This class intentionally avoids SDK coupling and uses direct HTTP requests,
    so business code does not import vendor SDKs.
    """

    def __init__(
        self,
        *,
        model_name: str,
        api_key: str,
        api_base: Optional[str] = None,
        retries: int = 2,
        default_timeout_s: float = 30.0,
    ):
        self._model_name = self._resolve_model_name(model_name)
        self._api_key = api_key
        self._api_base = (api_base or os.getenv("TONGYI_API_BASE") or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        self._retries = retries
        self._default_timeout_s = default_timeout_s
        self._dimension_cache: Optional[int] = None
        self._max_batch_size = 10

        self._request_count = 0
        self._latency_total_ms = 0.0

    @staticmethod
    def _resolve_model_name(requested_model_name: str) -> str:
        """Resolve planned v2.3 model aliases to compatible-mode model IDs.

        This keeps API-first call sites stable while allowing runtime swap to
        provider-supported model IDs without changing business-layer code.
        """
        alias_map = {
            "tongyi-embedding-vision-flash-2026-03-06": "text-embedding-v3",
            "tongyi-embedding-vision-plus-2026-03-06": "text-embedding-v4",
        }

        # Optional runtime override: "alias1=real1,alias2=real2"
        # Example:
        # TONGYI_MODEL_ALIAS_MAP="tongyi-embedding-vision-flash-2026-03-06=text-embedding-v4"
        raw_override = os.getenv("TONGYI_MODEL_ALIAS_MAP", "").strip()
        if raw_override:
            for pair in raw_override.split(","):
                if "=" not in pair:
                    continue
                src, dst = pair.split("=", 1)
                src = src.strip()
                dst = dst.strip()
                if src and dst:
                    alias_map[src] = dst

        resolved = alias_map.get(requested_model_name, requested_model_name)
        if resolved != requested_model_name:
            logger.info(
                "Tongyi model alias resolved",
                provider="tongyi",
                requested_model=requested_model_name,
                resolved_model=resolved,
            )
        return resolved

    def name(self) -> str:
        return "tongyi"

    def model_name(self) -> str:
        return self._model_name

    def supports_image(self) -> bool:
        return True

    def dimension(self) -> int:
        if self._dimension_cache is None:
            vecs = self.embed_texts(["dimension probe text"])
            if not vecs or not vecs[0]:
                raise ProviderBadResponse("Probe returned empty embedding vector", provider=self.name(), model_name=self.model_name())
            self._dimension_cache = len(vecs[0])
        return self._dimension_cache

    def metrics(self) -> Dict[str, Any]:
        avg = self._latency_total_ms / self._request_count if self._request_count else 0.0
        return {
            "request_count": self._request_count,
            "total_latency_ms": round(self._latency_total_ms, 3),
            "avg_latency_ms": round(avg, 3),
            "estimated_cost": 0.0,
        }

    def embed_texts(self, texts: List[str], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        if not texts:
            return []
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self._max_batch_size):
            payload = {
                "model": self._model_name,
                "input": texts[start : start + self._max_batch_size],
                "encoding_format": "float",
            }
            vectors.extend(self._post_embeddings(payload, timeout_s=timeout_s))
        return vectors

    def embed_multimodal(self, items: List[Dict[str, Any]], *, timeout_s: Optional[float] = None) -> List[List[float]]:
        if not items:
            return []

        encoded_items: List[Any] = []
        for item in items:
            if "text" in item and item["text"]:
                encoded_items.append(item["text"])
                continue
            if "image_path" in item and item["image_path"]:
                with open(item["image_path"], "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                encoded_items.append({"image": f"data:image/png;base64,{encoded}"})
                continue
            raise ProviderBadResponse("Unsupported multimodal item format", provider=self.name(), model_name=self.model_name(), context={"item_keys": list(item.keys())})

        vectors: List[List[float]] = []
        for start in range(0, len(encoded_items), self._max_batch_size):
            payload = {
                "model": self._model_name,
                "input": encoded_items[start : start + self._max_batch_size],
                "encoding_format": "float",
            }
            vectors.extend(self._post_embeddings(payload, timeout_s=timeout_s))
        return vectors

    def _post_embeddings(self, payload: Dict[str, Any], *, timeout_s: Optional[float]) -> List[List[float]]:
        timeout = timeout_s or self._default_timeout_s
        url = f"{self._api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(self._retries + 1):
            t0 = time.perf_counter()
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                self._request_count += 1
                self._latency_total_ms += elapsed_ms

                if response.status_code == 401:
                    raise ProviderAuthError("Provider auth failed", provider=self.name(), model_name=self.model_name())
                if response.status_code == 429:
                    raise ProviderRateLimited("Provider rate limited", provider=self.name(), model_name=self.model_name())
                if response.status_code >= 500:
                    raise ProviderUnavailable(f"Provider unavailable: {response.status_code}", provider=self.name(), model_name=self.model_name())
                if response.status_code >= 400:
                    raise ProviderBadResponse(
                        f"Provider bad response: {response.status_code} {response.text[:200]}",
                        provider=self.name(),
                        model_name=self.model_name(),
                        context={"api_base": self._api_base},
                    )

                data = response.json()
                vectors = self._extract_vectors(data)
                logger.info(
                    "Tongyi embedding request success",
                    provider=self.name(),
                    model=self.model_name(),
                    batch_size=len(payload.get("input", [])) if isinstance(payload.get("input"), list) else 1,
                    latency_ms=round(elapsed_ms, 3),
                )
                return vectors

            except requests.Timeout as e:
                last_error = ProviderTimeout("Provider request timeout", provider=self.name(), model_name=self.model_name())
            except requests.RequestException as e:
                last_error = ProviderUnavailable(f"Network error: {e}", provider=self.name(), model_name=self.model_name())
            except ValueError as e:
                last_error = ProviderBadResponse(f"Invalid JSON response: {e}", provider=self.name(), model_name=self.model_name())
            except Exception as e:
                last_error = e

            if attempt < self._retries:
                logger.warning(
                    "Tongyi embedding retry",
                    provider=self.name(),
                    model=self.model_name(),
                    attempt=attempt + 1,
                    max_attempts=self._retries + 1,
                    error=str(last_error),
                )
                continue

        if isinstance(last_error, Exception):
            raise last_error
        raise ProviderUnavailable("Unknown provider error", provider=self.name(), model_name=self.model_name())

    @staticmethod
    def _extract_vectors(payload: Dict[str, Any]) -> List[List[float]]:
        # OpenAI-compatible
        data = payload.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict) and "embedding" in data[0]:
            return [row["embedding"] for row in data]

        # Some vendor payloads may return output.embeddings
        output = payload.get("output")
        if isinstance(output, dict):
            emb = output.get("embeddings")
            if isinstance(emb, list) and emb and isinstance(emb[0], list):
                return emb

        raise ProviderBadResponse("Embedding vectors missing in provider response")
