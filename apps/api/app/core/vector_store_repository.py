"""Vector store repository abstraction for retrieval read paths.

Keeps Milvus-specific hit formatting at the storage boundary and exposes a
canonical chunk contract to search orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.milvus_service import MilvusService, get_milvus_service
from app.models.retrieval import RetrievedChunk, SearchConstraints


class VectorStoreRepository(ABC):
    """Abstract read-only vector store contract."""

    @abstractmethod
    def search(
        self,
        *,
        embedding: List[float],
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
    ) -> List[RetrievedChunk]:
        """Search the underlying vector store and return canonical chunks."""


class MilvusVectorStoreRepository(VectorStoreRepository):
    """Milvus-backed repository for canonical retrieval results."""

    def __init__(self, milvus_service: Optional[MilvusService] = None):
        self.milvus_service = milvus_service or get_milvus_service()

    @staticmethod
    def _normalize_hit(hit: dict) -> RetrievedChunk:
        score = hit.get("score")
        if score is None:
            score = hit.get("similarity")
        if score is None:
            score = 1 - float(hit.get("distance", 0.5))

        return RetrievedChunk(
            paper_id=hit.get("paper_id", ""),
            paper_title=hit.get("paper_title"),
            text=hit.get("text") or hit.get("content_data") or hit.get("content") or "",
            score=max(0.0, min(float(score), 1.0)),
            source_id=(str(hit.get("id")) if hit.get("id") is not None else None),
            page_num=hit.get("page_num") or hit.get("page"),
            section_path=hit.get("section_path"),
            content_subtype=hit.get("content_subtype"),
            anchor_text=hit.get("anchor_text"),
            section=hit.get("section"),
            content_type=hit.get("content_type", "text"),
            quality_score=hit.get("quality_score"),
            raw_data=hit.get("raw_data"),
        )

    def search(
        self,
        *,
        embedding: List[float],
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
    ) -> List[RetrievedChunk]:
        hits = self.milvus_service.search_contents_v2(
            embedding=embedding,
            user_id=user_id,
            content_type=content_type,
            top_k=top_k,
            constraints=constraints,
        )
        return [self._normalize_hit(hit) for hit in hits]


_vector_store_repository: Optional[VectorStoreRepository] = None


def get_vector_store_repository() -> VectorStoreRepository:
    """Get or create the default vector store repository singleton."""
    global _vector_store_repository
    if _vector_store_repository is None:
        _vector_store_repository = MilvusVectorStoreRepository()
    return _vector_store_repository