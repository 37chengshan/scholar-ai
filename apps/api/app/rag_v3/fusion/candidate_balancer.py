from __future__ import annotations

from collections import defaultdict

from app.rag_v3.schemas import EvidenceCandidate


BALANCE_FAMILIES = {
    "compare",
    "cross_paper",
    "survey",
    "related_work",
    "method_evolution",
    "conflicting_evidence",
}


def balance_candidates(
    candidates: list[EvidenceCandidate],
    query_family: str,
    per_paper_min_quota: int = 2,
    max_candidates: int = 180,
) -> list[EvidenceCandidate]:
    if query_family not in BALANCE_FAMILIES:
        return candidates[:max_candidates]

    by_paper: dict[str, list[EvidenceCandidate]] = defaultdict(list)
    for item in candidates:
        by_paper[item.paper_id].append(item)

    selected: list[EvidenceCandidate] = []
    for paper_id in sorted(by_paper.keys()):
        quota = by_paper[paper_id][:per_paper_min_quota]
        selected.extend(quota)

    seen = {item.source_chunk_id for item in selected}
    for item in candidates:
        if item.source_chunk_id in seen:
            continue
        selected.append(item)
        seen.add(item.source_chunk_id)
        if len(selected) >= max_candidates:
            break

    return selected[:max_candidates]
