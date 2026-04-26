from __future__ import annotations

from app.rag_v3.schemas import EvidenceCandidate


def rerank_candidates(query: str, candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    """Adapter slot for qwen3-vl-rerank.

    PR-1 keeps a deterministic ordering to stabilize tests before wiring the real model.
    """
    ranked = sorted(candidates, key=lambda item: item.rrf_score, reverse=True)
    for index, item in enumerate(ranked, start=1):
        item.post_rerank_rank = index
        item.rerank_score = max(0.0, 1.0 - (index - 1) / max(len(ranked), 1))
    return ranked
