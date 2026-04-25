"""Vector store repository abstraction for retrieval read paths.

Keeps Milvus-specific hit formatting at the storage boundary and exposes a
canonical chunk contract to search orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.config import settings
from app.core.bm25_service import SparseRecallService, get_sparse_recall_service
from app.core.milvus_service import MilvusService, get_milvus_service
from app.core.qdrant_service import QdrantService, get_qdrant_service
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

    @abstractmethod
    def search_sparse(
        self,
        *,
        query: str,
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
        prefetch_limit: int = 300,
    ) -> List[RetrievedChunk]:
        """Run sparse lexical recall and return canonical chunks."""

    def search_summary_index(
        self,
        *,
        embedding: List[float],
        user_id: str,
        top_k: int,
        constraints: SearchConstraints,
        summary_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search the summary index for global / survey queries.

        Default implementation returns empty list (backends that don't support
        the summary index gracefully degrade).
        """
        return []


class MilvusVectorStoreRepository(VectorStoreRepository):
    """Milvus-backed repository for canonical retrieval results."""

    def __init__(self, milvus_service: Optional[MilvusService] = None):
        self.milvus_service = milvus_service or get_milvus_service()
        self.sparse_service: SparseRecallService = get_sparse_recall_service()

    @staticmethod
    def _normalize_hit(hit: dict) -> RetrievedChunk:
        score = hit.get("score")
        if score is None:
            score = hit.get("similarity")
        if score is None:
            score = 1 - float(hit.get("distance", 0.5))

        raw_data = hit.get("raw_data") or {}

        evidence_types = hit.get("evidence_types") or raw_data.get("evidence_types")
        if isinstance(evidence_types, str):
            evidence_types = [evidence_types]
        if not evidence_types:
            evidence_types = [hit.get("content_type")] if hit.get("content_type") else []

        return RetrievedChunk(
            paper_id=hit.get("paper_id", ""),
            paper_title=hit.get("paper_title"),
            text=hit.get("text") or hit.get("content_data") or hit.get("content") or "",
            text_span=hit.get("text_span") or raw_data.get("text_span"),
            score=max(0.0, min(float(score), 1.0)),
            backend=hit.get("backend", "milvus"),
            source_id=(str(hit.get("id")) if hit.get("id") is not None else None),
            page_num=hit.get("page_num") or hit.get("page"),
            section_path=hit.get("section_path"),
            content_subtype=hit.get("content_subtype"),
            anchor_text=hit.get("anchor_text"),
            section=hit.get("section"),
            paper_role=hit.get("paper_role") or raw_data.get("paper_role"),
            table_ref=hit.get("table_ref") or raw_data.get("table_ref"),
            figure_ref=hit.get("figure_ref") or raw_data.get("figure_ref"),
            metric_sentence=hit.get("metric_sentence") or raw_data.get("metric_sentence"),
            dataset=hit.get("dataset") or raw_data.get("dataset") or raw_data.get("dataset_name"),
            baseline=hit.get("baseline") or raw_data.get("baseline") or raw_data.get("baseline_name"),
            method=hit.get("method") or raw_data.get("method") or raw_data.get("method_name"),
            score_value=hit.get("score_value") or raw_data.get("score_value") or raw_data.get("metric_value"),
            metric_name=hit.get("metric_name") or raw_data.get("metric_name"),
            metric_direction=hit.get("metric_direction") or raw_data.get("metric_direction"),
            caption_text=hit.get("caption_text") or raw_data.get("caption_text"),
            evidence_bundle_id=hit.get("evidence_bundle_id") or raw_data.get("evidence_bundle_id"),
            evidence_types=evidence_types,
            content_type=hit.get("content_type", "text"),
            quality_score=hit.get("quality_score"),
            raw_data=hit.get("raw_data"),
            vector_score=hit.get("vector_score"),
            sparse_score=hit.get("sparse_score"),
            hybrid_score=hit.get("hybrid_score"),
            reranker_score=hit.get("reranker_score"),
            retrieval_trace_id=hit.get("retrieval_trace_id"),
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

    def search_sparse(
        self,
        *,
        query: str,
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
        prefetch_limit: int = 300,
    ) -> List[RetrievedChunk]:
        collection = self.milvus_service.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)
        effective_constraints = constraints.model_copy(update={"content_types": [content_type]})
        expr = self.milvus_service._build_expr_from_constraints(effective_constraints)

        rows = collection.query(
            expr=expr,
            output_fields=[
                "id",
                "paper_id",
                "page_num",
                "content_type",
                "section",
                "content_data",
                "quality_score",
            ],
            limit=max(top_k, prefetch_limit),
        )

        scored: List[dict] = []
        for row in rows:
            text = row.get("content_data") or ""
            sparse_score = self.sparse_service.score(query, text)
            if sparse_score <= 0.0:
                continue
            scored.append(
                {
                    "id": row.get("id"),
                    "paper_id": row.get("paper_id"),
                    "page_num": row.get("page_num"),
                    "content_type": row.get("content_type") or content_type,
                    "section": row.get("section"),
                    "content_data": text,
                    "quality_score": row.get("quality_score"),
                    "score": sparse_score,
                    "sparse_score": sparse_score,
                    "backend": "milvus",
                    "raw_data": {},
                }
            )

        scored.sort(key=lambda item: float(item.get("sparse_score") or 0.0), reverse=True)
        return [self._normalize_hit(hit) for hit in scored[:top_k]]

    def search_summary_index(
        self,
        *,
        embedding: List[float],
        user_id: str,
        top_k: int,
        constraints: SearchConstraints,
        summary_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search the Iteration 2 summary index (paper_summaries collection)."""
        paper_ids = list(constraints.paper_ids) if constraints.paper_ids else None
        hits = self.milvus_service.search_summaries(
            embedding=embedding,
            user_id=user_id,
            top_k=top_k,
            paper_ids=paper_ids,
            summary_type=summary_type,
        )
        return [self._normalize_hit(hit) for hit in hits]


class QdrantVectorStoreRepository(VectorStoreRepository):
    """Qdrant-backed repository for retrieval experiment parity."""

    def __init__(self, qdrant_service: Optional[QdrantService] = None):
        self.qdrant_service = qdrant_service or get_qdrant_service()

    def search(
        self,
        *,
        embedding: List[float],
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
    ) -> List[RetrievedChunk]:
        hits = self.qdrant_service.search(
            embedding=embedding,
            user_id=user_id,
            content_type=content_type,
            top_k=top_k,
            constraints=constraints,
        )
        return [
            MilvusVectorStoreRepository._normalize_hit(
                {
                    **(hit.get("payload") or {}),
                    **hit,
                    "backend": hit.get("backend") or "qdrant",
                }
            )
            for hit in hits
        ]

    def search_sparse(
        self,
        *,
        query: str,
        user_id: str,
        content_type: str,
        top_k: int,
        constraints: SearchConstraints,
        prefetch_limit: int = 300,
    ) -> List[RetrievedChunk]:
        # Qdrant sparse recall can be added later with BM25/keyword index integration.
        return []


_vector_store_repository: Optional[VectorStoreRepository] = None


def get_vector_store_repository() -> VectorStoreRepository:
    """Get or create the default vector store repository singleton."""
    global _vector_store_repository
    if _vector_store_repository is None:
        if settings.VECTOR_STORE_BACKEND == "qdrant":
            _vector_store_repository = QdrantVectorStoreRepository()
        else:
            _vector_store_repository = MilvusVectorStoreRepository()
    return _vector_store_repository