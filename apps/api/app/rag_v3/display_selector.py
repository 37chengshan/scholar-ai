"""Display mode selection and query classification for RAG evidence.

Extracted from main_path_service.py to keep the orchestration layer under 800 lines.
"""

from __future__ import annotations

import re
from typing import Any

from app.rag_v3.schemas import EvidenceCandidate
from app.rag_v3.prompt_builder import _is_low_signal_compare_candidate

_QUERY_PREFIX_PATTERN = re.compile(r"^\s*(再次回答|继续分析|继续回答|继续|重新回答|重新分析|再回答一遍|重新来过)\s*[:：,，-]?\s*", re.IGNORECASE)
_CONTRIBUTION_QUERY_PATTERN = re.compile(
    r"(核心贡献|主要贡献|贡献点|创新点|创新|主要解决.*问题|解决.*问题|研究问题|研究动机|motivation|contribution|problem)",
    re.IGNORECASE,
)
_SUMMARY_SECTION_HINTS = ("abstract", "introduction", "motivation", "contribution", "summary", "overview")
_SUMMARY_SECTION_IDS = {"_paper", "paper_summary", "summary"}


def normalize_query_text(query: str) -> str:
    normalized = (query or "").strip()
    while True:
        cleaned = _QUERY_PREFIX_PATTERN.sub("", normalized)
        if cleaned == normalized:
            break
        normalized = cleaned.strip()
    return normalized


def is_summary_seeking_query(query: str) -> bool:
    return bool(_CONTRIBUTION_QUERY_PATTERN.search(query or ""))


def is_compare_family(query_family: str | None) -> bool:
    return query_family in {"compare", "cross_paper", "survey", "related_work", "method_evolution", "conflicting_evidence"}


def should_merge_summary_candidates(*, query: str, query_family: str | None) -> bool:
    normalized_family = str(query_family or "").strip().lower()
    return is_summary_seeking_query(query) or is_compare_family(query_family) or normalized_family == "evolution"


def is_summary_candidate(candidate: EvidenceCandidate) -> bool:
    section_id = (candidate.section_id or "").strip().lower()
    if section_id in _SUMMARY_SECTION_IDS:
        return True
    return "summary_index" in candidate.candidate_sources


def select_display_candidates(
    candidates: list[EvidenceCandidate],
    *,
    top_k: int,
    query_family: str | None,
) -> list[EvidenceCandidate]:
    if not candidates:
        return []

    if not is_compare_family(query_family):
        return candidates[:top_k]

    high_signal = [
        candidate
        for candidate in candidates
        if not is_summary_candidate(candidate) and not _is_low_signal_compare_candidate(candidate)
    ]
    if high_signal:
        return high_signal[:top_k]

    without_summary = [candidate for candidate in candidates if not is_summary_candidate(candidate)]
    if without_summary:
        return without_summary[:top_k]

    without_low_signal = [candidate for candidate in candidates if not _is_low_signal_compare_candidate(candidate)]
    if without_low_signal:
        return without_low_signal[:top_k]

    return candidates[:top_k]
