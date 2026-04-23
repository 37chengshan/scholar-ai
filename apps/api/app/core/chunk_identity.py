"""Stable chunk identity and chunk span matching helpers."""

from __future__ import annotations

import hashlib


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def build_stable_chunk_id(
    paper_id: str,
    page_num: int,
    normalized_section_path: str,
    char_start: int,
    char_end: int,
) -> str:
    """Build deterministic chunk id from stable anchors."""
    raw = "|".join(
        [
            str(paper_id or ""),
            str(_to_int(page_num)),
            str(normalized_section_path or ""),
            str(_to_int(char_start)),
            str(_to_int(char_end)),
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"chunk_{digest[:24]}"


def spans_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    """Return True when two inclusive-exclusive spans overlap."""
    a_start = _to_int(start_a)
    a_end = max(_to_int(end_a), a_start)
    b_start = _to_int(start_b)
    b_end = max(_to_int(end_b), b_start)
    return max(a_start, b_start) < min(a_end, b_end)
