"""Normalization helpers for user-facing paper metadata.

This module exists to keep bad parser output and fixture-like placeholder data
out of product UI without requiring every endpoint or page to hand-roll its
own display fallback logic.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


_PLACEHOLDER_TITLE_PATTERNS = [
    re.compile(r"^test paper\b", re.IGNORECASE),
    re.compile(r"^page\s+\d+\b", re.IGNORECASE),
    re.compile(r"^(untitled|unknown|document|paper)$", re.IGNORECASE),
]

_TITLE_NOISE_PATTERNS = [
    re.compile(r"\bthis paper demonstrates\b", re.IGNORECASE),
    re.compile(r"\bparallel extraction\b", re.IGNORECASE),
]

_SUMMARY_STYLE_TITLE_PREFIX_PATTERNS = [
    re.compile(r"^(?:this|the)\s+paper\b", re.IGNORECASE),
    re.compile(r"^(?:problem|research question|motivation|background|overview|method|results?|conclusion|future work)\b", re.IGNORECASE),
    re.compile(r"^(?:problem addressed)\b", re.IGNORECASE),
    re.compile(r"^(?:该论文|本文|研究|提出|主要解决|针对)\b"),
]

_SUMMARY_STYLE_TITLE_BODY_PATTERNS = [
    re.compile(r"\b(?:focuses on|addresses|demonstrates|introduces|proposes|presents|studies|explores|investigates|describes|evaluates|shows|relies on|suffers from)\b", re.IGNORECASE),
    re.compile(r"\bproblem addressed\b", re.IGNORECASE),
]

_AUTHOR_NOISE_PATTERNS = [
    re.compile(r"\bthis paper demonstrates\b", re.IGNORECASE),
    re.compile(r"\bparallel extraction\b", re.IGNORECASE),
    re.compile(r"[.!?;:]\s*$"),
]

_VENUE_PLACEHOLDER_PATTERNS = [
    re.compile(r"^(unknown|n/?a|none|null|test)$", re.IGNORECASE),
]

_DEFAULT_UNTITLED_PAPER_TITLE = "未命名论文"


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _filename_stem(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    stem = re.sub(r"\.pdf$", "", text, flags=re.IGNORECASE).strip()
    return stem or None


def _normalize_page_suffixed_title(title: str | None) -> str | None:
    text = _clean_text(title)
    if not text:
        return None
    return re.sub(r"\s*[-–—:]\s*page\s+\d+\s*$", "", text, flags=re.IGNORECASE).strip() or text


def _looks_like_bad_title(title: str | None) -> bool:
    if not title:
        return True

    normalized_title = _normalize_page_suffixed_title(title) or title
    lowered = normalized_title.lower()
    if any(pattern.search(normalized_title) for pattern in _PLACEHOLDER_TITLE_PATTERNS):
        return True
    if any(pattern.search(lowered) for pattern in _TITLE_NOISE_PATTERNS):
        return True
    if any(pattern.search(normalized_title) for pattern in _SUMMARY_STYLE_TITLE_PREFIX_PATTERNS):
        return True
    if (
        len(normalized_title) >= 48
        and any(pattern.search(normalized_title) for pattern in _SUMMARY_STYLE_TITLE_BODY_PATTERNS)
    ):
        return True
    if len(normalized_title) < 6:
        return True
    return False


def is_plausible_extracted_title(title: Any) -> bool:
    return not _looks_like_bad_title(_clean_text(title))


def _looks_like_bad_author(author: str | None) -> bool:
    if not author:
        return True
    if len(author) < 2 or len(author) > 80:
        return True
    if any(pattern.search(author) for pattern in _AUTHOR_NOISE_PATTERNS):
        return True
    tokens = author.split()
    if len(tokens) >= 6:
        return True
    return False


def _normalize_authors(authors: Iterable[Any] | None) -> list[str]:
    if not authors:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in authors:
        text = _clean_text(raw)
        if _looks_like_bad_author(text):
            continue
        assert text is not None
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def normalize_extracted_authors(authors: Iterable[Any] | None) -> list[str]:
    return _normalize_authors(authors)


def _normalize_venue(venue: Any) -> str | None:
    text = _clean_text(venue)
    if not text:
        return None
    if any(pattern.search(text) for pattern in _VENUE_PLACEHOLDER_PATTERNS):
        return None
    return text


def _normalize_year(year: Any) -> int | None:
    if not isinstance(year, int):
        return None
    if year < 1900 or year > 2100:
        return None
    return year


def sanitize_paper_display_metadata(
    *,
    paper_id: str,
    title: Any,
    authors: Iterable[Any] | None,
    year: Any = None,
    venue: Any = None,
    fallback_title: Any = None,
) -> dict[str, Any]:
    cleaned_title = _normalize_page_suffixed_title(title)
    normalized_authors = _normalize_authors(authors)
    normalized_year = _normalize_year(year)
    normalized_venue = _normalize_venue(venue)
    normalized_fallback_title = _filename_stem(fallback_title)

    if _looks_like_bad_title(cleaned_title):
        if normalized_authors:
            fallback = normalized_authors[0]
            cleaned_title = f"{fallback} 的论文" if re.search(r"[\u4e00-\u9fff]", fallback) else f"Paper by {fallback}"
        elif normalized_fallback_title and not _looks_like_bad_title(normalized_fallback_title):
            cleaned_title = normalized_fallback_title
        elif normalized_fallback_title:
            cleaned_title = normalized_fallback_title
        else:
            cleaned_title = _DEFAULT_UNTITLED_PAPER_TITLE

    return {
        "title": cleaned_title,
        "authors": normalized_authors,
        "year": normalized_year,
        "venue": normalized_venue,
    }
