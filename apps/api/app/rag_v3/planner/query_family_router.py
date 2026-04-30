from __future__ import annotations

import re
from typing import Final

QUERY_FAMILIES: Final[set[str]] = {
    "fact",
    "method",
    "table",
    "figure",
    "numeric",
    "compare",
    "cross_paper",
    "survey",
    "related_work",
    "method_evolution",
    "conflicting_evidence",
    "hard",
}


def normalize_query_family(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in QUERY_FAMILIES:
        return normalized
    return "fact"


def infer_query_family(query: str) -> str:
    text = str(query or "").lower()

    if re.search(r"\b(conflict|contradict|inconsistent|disagree)\b", text) or re.search(
        r"争议|矛盾|冲突",
        text,
    ):
        return "conflicting_evidence"
    if re.search(r"\b(survey|literature review|related work)\b", text) or re.search(
        r"综述|研究现状",
        text,
    ):
        if "related work" in text:
            return "related_work"
        return "survey"
    if re.search(r"\b(evolution|timeline|history)\b", text) or re.search(
        r"发展脉络|演进",
        text,
    ):
        return "method_evolution"
    if re.search(r"\b(hard|open problem|why is .* difficult)\b", text) or re.search(
        r"挑战|难点",
        text,
    ):
        return "hard"
    if re.search(r"\b(table|tab\.|rows?|columns?|figure|fig\.|caption)\b", text):
        if "figure" in text or "fig." in text:
            return "figure"
        if "table" in text or "tab." in text:
            return "table"
    if re.search(r"\b(compare|versus|vs\.?|difference|better than|worse than)\b", text):
        return "compare"
    if re.search(r"\b(across papers|cross paper|cross-paper)\b", text):
        return "cross_paper"
    if re.search(r"\b(accuracy|f1|bleu|rouge|recall@|precision@|latency|p-value|percent|%)\b", text):
        return "numeric"
    if re.search(r"\b(method|approach|architecture|algorithm|pipeline)\b", text):
        return "method"
    return "fact"
