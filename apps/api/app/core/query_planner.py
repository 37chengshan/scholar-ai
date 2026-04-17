"""Lightweight query planner for hybrid RAG retrieval.

Builds multiple query variants for dense + sparse retrieval paths.
"""

import re
from typing import List


STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "to",
    "in",
    "for",
    "on",
    "is",
    "are",
    "what",
    "how",
    "why",
    "with",
    "by",
    "from",
    "that",
    "this",
    "这",
    "那个",
    "这个",
    "以及",
    "如何",
    "什么",
    "哪些",
}


def _extract_keywords(query: str) -> List[str]:
    """Extract lightweight keywords from a mixed Chinese/English query."""
    if not query:
        return []

    terms = re.findall(r"[a-zA-Z0-9_\-]+|[\u4e00-\u9fff]{2,}", query.lower())
    keywords: List[str] = []
    for term in terms:
        if term in STOPWORDS:
            continue
        if term.isdigit():
            continue
        if len(term) < 2:
            continue
        keywords.append(term)
    return keywords


def plan_queries(query: str, query_intent: str) -> List[str]:
    """Generate deterministic query variants for hybrid retrieval.

    Returns de-duplicated variants in priority order:
    1) raw query
    2) keyword-heavy query
    3) intent-aware expansion query
    """
    planned: List[str] = []

    raw = (query or "").strip()
    if raw:
        planned.append(raw)

    keywords = _extract_keywords(raw)
    if keywords:
        planned.append(" ".join(keywords[:10]))

    intent = (query_intent or "").lower()
    if intent == "compare":
        planned.append(f"{raw} 对比 差异 指标")
    elif intent == "evolution":
        planned.append(f"{raw} 时间线 演化 变化")
    elif intent == "summary":
        planned.append(f"{raw} 关键结论 方法 结果")

    if any(token in raw.lower() for token in ["table", "figure", "图", "表"]):
        planned.append(f"{raw} table figure caption")

    deduped: List[str] = []
    for q in planned:
        q = q.strip()
        if q and q not in deduped:
            deduped.append(q)

    return deduped[:4]
