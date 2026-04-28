"""HybridRetriever – Phase 4 multi-paper retrieval pipeline.

Pipeline:
  1. Per-paper dense retrieval (enforces per-paper evidence budget)
  2. Sparse / keyword retrieval (existing SparseEvidenceRetriever)
  3. RRF fusion across dense + sparse signals
  4. Rerank with rerank_score / pre_rerank_rank / post_rerank_rank trace
  5. Return balanced EvidencePack with rerank trace written to diagnostics

Design constraints:
- No single paper may dominate the fused candidate set.
  Each paper is allocated at most `per_paper_budget` candidates before fusion.
- Rerank trace fields (pre_rerank_rank, post_rerank_rank, rerank_score, rerank_gain)
  are written to every EvidenceCandidate so Phase 6 benchmarks can consume them.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.rag_v3.fusion.rrf_fusion import rrf_fuse, trim_candidates
from app.rag_v3.rerank.qwen3vl_rerank_adapter import rerank_candidates
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.sparse_evidence_retriever import SparseEvidenceRetriever
from app.rag_v3.schemas import EvidenceCandidate, EvidencePack


_DEFAULT_PER_PAPER_BUDGET = 8
_DEFAULT_SPARSE_TOP_K = 20
_DEFAULT_RERANK_TOP_K = 10


def _tag_pre_rerank_ranks(candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    """Write pre_rerank_rank in-place and return the list."""
    for rank, cand in enumerate(candidates, start=1):
        cand.pre_rerank_rank = rank
    return candidates


def _compute_rerank_gain(
    candidates: list[EvidenceCandidate],
) -> list[EvidenceCandidate]:
    """Compute rerank_gain = pre_rerank_rank - post_rerank_rank for each candidate."""
    for cand in candidates:
        if cand.pre_rerank_rank > 0 and cand.post_rerank_rank > 0:
            # positive means reranker promoted this candidate
            object.__setattr__(cand, "__dict__", cand.__dict__)  # ensure mutable
            cand.__dict__["rerank_gain"] = cand.pre_rerank_rank - cand.post_rerank_rank
    return candidates


class HybridRetriever:
    """Multi-paper hybrid retrieval with per-paper budget and rerank trace.

    Parameters
    ----------
    dense_retriever:
        DenseEvidenceRetriever instance.  If None, a stub is used (unit-test
        mode: returns empty list).
    sparse_retriever:
        SparseEvidenceRetriever instance.  Defaults to the existing stub.
    per_paper_budget:
        Maximum candidates collected per paper from the dense phase before
        fusion.  Prevents high-recall papers from crowding the matrix.
    rerank_top_k:
        Number of candidates to keep after reranking.
    """

    def __init__(
        self,
        *,
        dense_retriever: DenseEvidenceRetriever | None = None,
        sparse_retriever: SparseEvidenceRetriever | None = None,
        per_paper_budget: int = _DEFAULT_PER_PAPER_BUDGET,
        rerank_top_k: int = _DEFAULT_RERANK_TOP_K,
    ) -> None:
        self._dense = dense_retriever or DenseEvidenceRetriever()
        self._sparse = sparse_retriever or SparseEvidenceRetriever()
        self._per_paper_budget = per_paper_budget
        self._rerank_top_k = rerank_top_k

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        paper_ids: list[str],
        *,
        section_paths: list[str] | None = None,
        content_types: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        query_family: str = "compare",
    ) -> EvidencePack:
        """Run hybrid retrieval for multi-paper compare.

        For each paper in *paper_ids* we run a dedicated dense search with the
        paper scoped filter, then cap results to *per_paper_budget*.  This
        guarantees every paper contributes to the evidence pool before fusion.
        """
        # ---- Phase A: per-paper dense retrieval --------------------------
        per_paper_candidates: dict[str, list[EvidenceCandidate]] = {}
        for pid in paper_ids:
            candidates = self._dense.retrieve(
                query=query,
                top_k=self._per_paper_budget,
                paper_id_filter=[pid],
                section_paths=section_paths,
                page_from=page_from,
                page_to=page_to,
                content_types=content_types,
            )
            per_paper_candidates[pid] = candidates[: self._per_paper_budget]

        all_dense = [c for cs in per_paper_candidates.values() for c in cs]

        # ---- Phase B: sparse / keyword retrieval -------------------------
        sparse_candidates = self._sparse.retrieve(
            query=query, top_k=_DEFAULT_SPARSE_TOP_K
        )

        # ---- Phase C: RRF fusion -----------------------------------------
        source_map: dict[str, list[EvidenceCandidate]] = {
            "dense": all_dense,
            "sparse": sparse_candidates,
        }
        fused = rrf_fuse(source_map)

        # Cap before rerank
        pre_rerank = trim_candidates(fused, self._rerank_top_k * 3)

        # Tag pre-rerank positions
        _tag_pre_rerank_ranks(pre_rerank)

        # ---- Phase D: Rerank ---------------------------------------------
        reranked = rerank_candidates(query=query, candidates=pre_rerank)
        _compute_rerank_gain(reranked)
        final = trim_candidates(reranked, self._rerank_top_k)

        # ---- Diagnostics -------------------------------------------------
        query_id = f"hybrid-{uuid4().hex[:8]}"
        paper_coverage = len({c.paper_id for c in final})
        missing_papers = [
            pid for pid in paper_ids if pid not in {c.paper_id for c in final}
        ]
        diagnostics: dict[str, float] = {
            "dense_candidates_total": float(len(all_dense)),
            "sparse_candidates_total": float(len(sparse_candidates)),
            "fused_before_rerank": float(len(pre_rerank)),
            "paper_coverage_count": float(paper_coverage),
            "missing_paper_count": float(len(missing_papers)),
            "per_paper_budget": float(self._per_paper_budget),
            "rerank_top_k": float(self._rerank_top_k),
        }

        return EvidencePack(
            query_id=query_id,
            query=query,
            query_family=query_family,  # type: ignore[arg-type]
            stage="hybrid",
            candidates=final,
            diagnostics=diagnostics,
        )
