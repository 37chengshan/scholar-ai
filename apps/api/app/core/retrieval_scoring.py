"""Scoring helpers for hybrid retrieval and reranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from app.core.bm25_service import SparseRecallService, get_sparse_recall_service


@dataclass(frozen=True)
class RetrievalScoreBreakdown:
    """Detailed scoring components for a single retrieval candidate."""

    vector_score: float
    sparse_score: float
    hybrid_score: float


class RetrievalScoringService:
    """Compute dense/sparse hybrid scores and apply reranker outputs."""

    def __init__(
        self,
        *,
        sparse_recall: SparseRecallService | None = None,
        vector_weight: float = 0.75,
        sparse_weight: float = 0.25,
    ):
        self.sparse_recall = sparse_recall or get_sparse_recall_service()
        self.vector_weight = vector_weight
        self.sparse_weight = sparse_weight

    @staticmethod
    def _clamp_score(value: Any) -> float:
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def build_structured_reranker_document(hit: Dict[str, Any]) -> str:
        text = hit.get("text") or hit.get("content_data") or hit.get("content") or ""
        paper_title = hit.get("paper_title") or hit.get("title") or ""
        section = hit.get("section") or ""
        page_num = hit.get("page_num") or hit.get("page") or ""
        content_type = hit.get("content_type") or "text"
        paper_role = hit.get("paper_role") or ""
        table_ref = hit.get("table_ref") or ""
        figure_ref = hit.get("figure_ref") or ""
        metric_name = hit.get("metric_name") or ""
        score_value = hit.get("score_value") or ""
        dataset = hit.get("dataset") or ""
        method = hit.get("method") or ""
        caption_text = hit.get("caption_text") or ""
        return (
            f"title: {paper_title}\n"
            f"section: {section}\n"
            f"page_num: {page_num}\n"
            f"content_type: {content_type}\n"
            f"paper_role: {paper_role}\n"
            f"table_ref: {table_ref}\n"
            f"figure_ref: {figure_ref}\n"
            f"metric_name: {metric_name}\n"
            f"score_value: {score_value}\n"
            f"dataset: {dataset}\n"
            f"method: {method}\n"
            f"caption_text: {caption_text}\n"
            f"text: {text}"
        )

    @staticmethod
    def build_compact_reranker_document(hit: Dict[str, Any]) -> str:
        """Backward-compatible compact document format used by older reranker flows."""
        text = hit.get("text") or hit.get("content_data") or hit.get("content") or ""
        paper_title = hit.get("paper_title") or hit.get("title") or ""
        section = hit.get("section") or ""
        page_num = hit.get("page_num") or hit.get("page") or ""
        content_type = hit.get("content_type") or "text"
        return (
            f"title: {paper_title}\n"
            f"section: {section}\n"
            f"page_num: {page_num}\n"
            f"content_type: {content_type}\n"
            f"text: {text}"
        )

    def score_candidate(
        self,
        *,
        query: str,
        candidate_text: str,
        raw_vector_score: Any,
    ) -> RetrievalScoreBreakdown:
        vector_score = self._clamp_score(raw_vector_score)
        sparse_score = self._clamp_score(self.sparse_recall.score(query, candidate_text))
        hybrid_score = self._clamp_score(
            (self.vector_weight * vector_score) + (self.sparse_weight * sparse_score)
        )
        return RetrievalScoreBreakdown(
            vector_score=vector_score,
            sparse_score=sparse_score,
            hybrid_score=hybrid_score,
        )

    def annotate_hybrid_scores(self, query: str, results: Iterable[Dict[str, Any]]) -> None:
        for result in results:
            scored = self.score_candidate(
                query=query,
                candidate_text=result.get("text") or result.get("content_data") or result.get("content") or "",
                raw_vector_score=result.get("score", result.get("similarity", 0.0)),
            )
            result["vector_score"] = scored.vector_score
            result["sparse_score"] = scored.sparse_score
            result["hybrid_score"] = scored.hybrid_score

    @staticmethod
    def fuse_branch_results(
        branch_results: Dict[str, List[Dict[str, Any]]],
        branch_weights: Dict[str, float],
        *,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Fuse heterogeneous branch results with weighted RRF.

        This is branch-agnostic and can combine dense/sparse/scientific branches.
        """
        fused: Dict[str, Dict[str, Any]] = {}

        for branch, results in branch_results.items():
            weight = float(branch_weights.get(branch, 0.0))
            if weight <= 0.0:
                continue

            for rank, result in enumerate(results, start=1):
                result_key = (
                    f"{result.get('paper_id', '')}:"
                    f"{result.get('content_type', 'text')}:"
                    f"{result.get('source_id') or result.get('id') or result.get('page_num') or rank}"
                )
                score = weight / (rrf_k + rank)

                if result_key not in fused:
                    fused[result_key] = {
                        **result,
                        "rrf_score": 0.0,
                        "branch_ranks": {},
                    }

                fused[result_key]["rrf_score"] += score
                fused[result_key]["branch_ranks"][branch] = rank

        merged = list(fused.values())
        merged.sort(key=lambda item: float(item.get("rrf_score", 0.0)), reverse=True)
        return merged

    def apply_reranker_scores(
        self,
        results: List[Dict[str, Any]],
        reranked: List[Any],
    ) -> List[Dict[str, Any]]:
        content_to_score: Dict[str, float] = {}
        for item in reranked:
            if isinstance(item, dict):
                document = item.get("document")
                score = item.get("score", 0.0)
            else:
                try:
                    document, score = item
                except (TypeError, ValueError):
                    continue

            if not isinstance(document, str):
                continue
            content_to_score[document] = self._clamp_score(score)

        for result in results:
            structured = self.build_structured_reranker_document(result)
            compact = self.build_compact_reranker_document(result)
            plain_text = result.get("text") or result.get("content_data") or result.get("content") or ""
            result["reranker_score"] = content_to_score.get(
                structured,
                content_to_score.get(compact, content_to_score.get(plain_text, 0.0)),
            )

        results.sort(key=lambda item: item.get("reranker_score", 0.0), reverse=True)
        return results