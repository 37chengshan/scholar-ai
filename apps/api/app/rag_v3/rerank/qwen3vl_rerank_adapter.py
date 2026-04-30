from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.core.dashscope_runtime import DashScopeRerankService, dashscope_is_configured
from app.core.runtime_contract import RuntimeBinding, build_shim_binding
from app.rag_v3.schemas import EvidenceCandidate


def _deterministic_rerank(candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    ranked = sorted(candidates, key=lambda item: item.rrf_score, reverse=True)
    for index, item in enumerate(ranked, start=1):
        item.post_rerank_rank = index
        item.rerank_score = max(0.0, 1.0 - (index - 1) / max(len(ranked), 1))
    return ranked


@lru_cache(maxsize=1)
def _get_dashscope_rerank_service() -> DashScopeRerankService:
    return DashScopeRerankService(
        model=settings.DASHSCOPE_RERANK_MODEL,
        provider_name="dashscope_qwen",
    )


def get_rerank_runtime_binding() -> RuntimeBinding:
    if dashscope_is_configured():
        return _get_dashscope_rerank_service().get_runtime_binding()
    return build_shim_binding(
        component="reranker",
        provider_name="dashscope_qwen",
        model=settings.DASHSCOPE_RERANK_MODEL,
        dimension=None,
    )


def rerank_candidates(query: str, candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    """Rerank candidates with DashScope when configured, else deterministic fallback."""
    if not candidates:
        return []

    if not dashscope_is_configured():
        return _deterministic_rerank(candidates)

    service = _get_dashscope_rerank_service()
    documents = [item.anchor_text or item.section_id or item.source_chunk_id for item in candidates]
    try:
        results = service.rerank(query=query, documents=documents, top_n=len(documents))
    except Exception:
        return _deterministic_rerank(candidates)

    by_index = {int(item["index"]): item for item in results}
    ordered: list[EvidenceCandidate] = []
    seen_indexes: set[int] = set()
    for rank, item in enumerate(results, start=1):
        index = int(item["index"])
        if index < 0 or index >= len(candidates) or index in seen_indexes:
            continue
        candidate = candidates[index]
        candidate.post_rerank_rank = rank
        candidate.rerank_score = float(item["score"])
        ordered.append(candidate)
        seen_indexes.add(index)

    if len(ordered) < len(candidates):
        remaining = [candidate for idx, candidate in enumerate(candidates) if idx not in seen_indexes]
        fallback_ranked = _deterministic_rerank(remaining)
        offset = len(ordered)
        for extra_rank, candidate in enumerate(fallback_ranked, start=1):
            candidate.post_rerank_rank = offset + extra_rank
            ordered.append(candidate)

    return ordered
