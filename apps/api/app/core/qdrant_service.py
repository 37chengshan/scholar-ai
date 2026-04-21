"""Optional Qdrant adapter for retrieval experiments."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.qdrant_filter_compiler import QdrantFilterCompiler
from app.core.qdrant_mapper import QdrantMapper
from app.models.retrieval import SearchConstraints


class QdrantService:
    """Thin wrapper around an optional Qdrant client."""

    def __init__(self, client: Optional[Any] = None):
        self._client = client
        self.filter_compiler = QdrantFilterCompiler()
        self.mapper = QdrantMapper()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required when VECTOR_STORE_BACKEND=qdrant"
            ) from exc

        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            prefer_grpc=False,
        )
        return self._client

    def search(
        self,
        *,
        embedding: List[float],
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        merged_constraints = constraints.model_copy(
            update={
                "user_id": user_id,
                "content_types": constraints.content_types or [content_type],
            }
        )
        backend_filter = self.filter_compiler.compile(merged_constraints)
        raw_results = client.search(
            collection_name=settings.QDRANT_COLLECTION_CONTENTS_V2,
            query_vector=embedding,
            query_filter=backend_filter,
            limit=top_k,
            with_payload=True,
        )
        return [self.mapper.to_hit(item) for item in raw_results]


_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service