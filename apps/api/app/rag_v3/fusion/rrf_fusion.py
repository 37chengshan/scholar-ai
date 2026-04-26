from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.rag_v3.schemas import EvidenceCandidate


def _rrf(rank: int, k: int = 60) -> float:
    return 1.0 / float(k + rank)


def rrf_fuse(source_ranked_candidates: dict[str, list[EvidenceCandidate]], k: int = 60) -> list[EvidenceCandidate]:
    fused: dict[str, EvidenceCandidate] = {}
    source_ranks: dict[str, dict[str, int]] = defaultdict(dict)

    for source, ranked in source_ranked_candidates.items():
        for index, candidate in enumerate(ranked, start=1):
            source_chunk_id = candidate.source_chunk_id
            if source_chunk_id not in fused:
                fused[source_chunk_id] = candidate.model_copy(deep=True)
                fused[source_chunk_id].candidate_sources = []
                fused[source_chunk_id].rrf_score = 0.0
            base = fused[source_chunk_id]
            if source not in base.candidate_sources:
                base.candidate_sources.append(source)
            base.rrf_score += _rrf(index, k=k)
            source_ranks[source_chunk_id][source] = index

    ranked_fused = sorted(fused.values(), key=lambda item: item.rrf_score, reverse=True)
    for index, candidate in enumerate(ranked_fused, start=1):
        candidate.pre_rerank_rank = index
    return ranked_fused


def trim_candidates(candidates: Iterable[EvidenceCandidate], limit: int) -> list[EvidenceCandidate]:
    return list(candidates)[: max(1, int(limit))]
