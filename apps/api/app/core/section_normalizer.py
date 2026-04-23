"""Canonical section taxonomy and normalization helpers."""

from __future__ import annotations

import re
from typing import Iterable, List

CANONICAL_SECTIONS = (
    "abstract",
    "introduction",
    "related_work",
    "method",
    "experiment",
    "result",
    "discussion",
    "conclusion",
    "limitation",
    "appendix",
)

_ALIASES = {
    "background": "introduction",
    "preliminaries": "introduction",
    "related work": "related_work",
    "literature review": "related_work",
    "methodology": "method",
    "approach": "method",
    "model": "method",
    "methods": "method",
    "experimental setup": "experiment",
    "evaluation": "experiment",
    "experiments": "experiment",
    "findings": "result",
    "results": "result",
    "analysis": "discussion",
    "future work": "limitation",
    "limitations": "limitation",
    "ablation": "experiment",
    "implementation details": "method",
    "conclusions": "conclusion",
    "supplementary": "appendix",
}


def _to_key(value: str) -> str:
    lowered = (value or "").strip().lower().replace("_", " ")
    lowered = re.sub(r"^[\d.\-\s]+", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def canonicalize_section_name(name: str) -> str:
    """Map raw section labels to a canonical taxonomy."""
    key = _to_key(name)
    if not key:
        return ""

    canonical_by_space = {item.replace("_", " "): item for item in CANONICAL_SECTIONS}
    if key in canonical_by_space:
        return canonical_by_space[key]

    if key in _ALIASES:
        return _ALIASES[key]

    for alias, canonical in sorted(_ALIASES.items(), key=lambda pair: len(pair[0]), reverse=True):
        if alias in key:
            return canonical

    return key.replace(" ", "_")


def normalize_section_path(raw_path: str | Iterable[str] | None) -> List[str]:
    """Normalize path segments and return canonical path tokens."""
    if raw_path is None:
        return []

    if isinstance(raw_path, str):
        segments = [seg.strip() for seg in re.split(r"\s*(?:/|>|\\|\||::)\s*", raw_path) if seg.strip()]
        if not segments and raw_path.strip():
            segments = [raw_path.strip()]
    else:
        segments = [str(seg).strip() for seg in raw_path if str(seg).strip()]

    normalized: List[str] = []
    for segment in segments:
        canonical = canonicalize_section_name(segment)
        if canonical and (not normalized or normalized[-1] != canonical):
            normalized.append(canonical)
    return normalized


def serialize_section_path(path_tokens: Iterable[str]) -> str:
    tokens = [token for token in path_tokens if token]
    return "/".join(tokens)


def section_leaf(path_tokens: Iterable[str]) -> str:
    tokens = [token for token in path_tokens if token]
    return tokens[-1] if tokens else ""


def section_parent_path(path_tokens: Iterable[str]) -> str:
    tokens = [token for token in path_tokens if token]
    if len(tokens) <= 1:
        return ""
    return "/".join(tokens[:-1])
