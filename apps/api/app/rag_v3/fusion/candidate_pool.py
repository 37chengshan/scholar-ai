from __future__ import annotations

from app.rag_v3.schemas import EvidenceCandidate


def build_candidate_pool(*candidate_lists: list[EvidenceCandidate], max_size: int = 180) -> list[EvidenceCandidate]:
    pool: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for candidates in candidate_lists:
        for candidate in candidates:
            if candidate.source_chunk_id in seen:
                continue
            pool.append(candidate)
            seen.add(candidate.source_chunk_id)
            if len(pool) >= max_size:
                return pool
    return pool
