"""Academic-aware query planner for hybrid RAG retrieval.

This module keeps the old `plan_queries()` API while adding a richer academic
planning output consumed by multimodal retrieval and evaluation.
"""

import re
from typing import Any, Dict, List


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

QUERY_FAMILIES = {
    "fact",
    "compare",
    "evolution",
    "critique",
    "limitation",
    "numeric",
    "figure",
    "table",
}

PAPER_ROLE_HINTS = ["method", "result", "limitation", "ablation", "conclusion"]


def classify_query_family(query: str, query_intent: str = "") -> str:
    """Classify a query into the academic query families."""
    text = (query or "").lower()
    intent = (query_intent or "").lower()

    if intent == "compare" or any(tok in text for tok in ["compare", "vs", "versus", "difference", "对比", "比较"]):
        return "compare"
    if intent == "evolution" or any(tok in text for tok in ["evolution", "timeline", "trend", "演化", "发展", "迭代"]):
        return "evolution"
    if any(tok in text for tok in ["figure", "fig.", "图", "caption"]):
        return "figure"
    if any(tok in text for tok in ["table", "tab.", "表"]):
        return "table"
    if any(tok in text for tok in ["accuracy", "f1", "auc", "score", "数值", "指标", "%", "率"]):
        return "numeric"
    if any(tok in text for tok in ["limitation", "局限", "不足", "weakness", "boundary"]):
        return "limitation"
    if any(tok in text for tok in ["critique", "批判", "critic", "challenge", "failure mode"]):
        return "critique"
    return "fact"


def _extract_entities(query: str) -> Dict[str, List[str]]:
    """Extract lightweight academic entities from query text."""
    raw = query or ""
    methods = re.findall(r"\b([A-Z][A-Za-z0-9\-]{2,})\b", raw)
    datasets = re.findall(r"\b([A-Z]{2,}(?:-[0-9]{2,})?)\b", raw)
    metrics = [
        tok
        for tok in ["accuracy", "f1", "auc", "precision", "recall", "bleu", "rouge"]
        if tok in raw.lower()
    ]
    objects = [
        tok
        for tok in ["method", "result", "table", "figure", "ablation", "baseline"]
        if tok in raw.lower()
    ]

    return {
        "methods": list(dict.fromkeys(methods[:5])),
        "datasets": list(dict.fromkeys(datasets[:5])),
        "metrics": list(dict.fromkeys(metrics[:5])),
        "objects": list(dict.fromkeys(objects[:5])),
    }


def _decontextualize_query(query: str, entities: Dict[str, List[str]]) -> str:
    """Rewrite pronoun-heavy query into explicit retrieval query."""
    rewritten = (query or "").strip()
    if not rewritten:
        return ""

    method = entities.get("methods", ["method"])[0] if entities.get("methods") else "method"
    dataset = entities.get("datasets", ["dataset"])[0] if entities.get("datasets") else "dataset"
    metric = entities.get("metrics", ["metric"])[0] if entities.get("metrics") else "metric"

    replacements = {
        "their method": f"{method} method",
        "this method": f"{method} method",
        "this result": f"{metric} result on {dataset}",
        "this table": f"table for {method} on {dataset}",
        "这个方法": f"{method} 方法",
        "这个结果": f"{dataset} 上 {metric} 结果",
        "这个表": f"{method} 在 {dataset} 的表格",
    }
    lowered = rewritten.lower()
    for src, dst in replacements.items():
        lowered = lowered.replace(src, dst)
    return lowered


def _sub_questions(query_family: str, decontextualized: str) -> List[Dict[str, str]]:
    """Generate deterministic sub-question plan by query family."""
    if query_family == "compare":
        return [
            {"role": "method_a_result", "question": f"What is method A result for: {decontextualized}?"},
            {"role": "method_b_result", "question": f"What is method B result for: {decontextualized}?"},
            {"role": "metric_difference", "question": f"What is the metric difference in: {decontextualized}?"},
            {"role": "applicability_condition", "question": f"Under what conditions does each method work for: {decontextualized}?"},
        ]
    if query_family == "evolution":
        return [
            {"role": "version_stages", "question": f"What are the version stages in: {decontextualized}?"},
            {"role": "key_changes", "question": f"What key changes happened over time in: {decontextualized}?"},
            {"role": "trend_summary", "question": f"Summarize the trend for: {decontextualized}."},
        ]
    if query_family in {"critique", "limitation"}:
        return [
            {"role": "author_stated_limitations", "question": f"What limitations are explicitly stated for: {decontextualized}?"},
            {"role": "experimental_boundaries", "question": f"What experimental boundaries constrain: {decontextualized}?"},
            {"role": "failure_modes", "question": f"What failure modes are reported for: {decontextualized}?"},
        ]
    return [{"role": "fact_lookup", "question": decontextualized}]


def _fallback_rewrites(query_family: str, decontextualized: str) -> List[str]:
    """Generate second-pass rewrites for weak first-pass retrieval."""
    seeds = [
        f"{decontextualized} evidence results methods",
        f"{decontextualized} experiments ablation",
    ]
    if query_family in {"numeric", "compare"}:
        seeds.append(f"{decontextualized} metric value table")
    if query_family == "figure":
        seeds.append(f"{decontextualized} figure caption visualization")
    if query_family == "table":
        seeds.append(f"{decontextualized} table row column metric")
    return [s.strip() for s in seeds if s.strip()][:3]


def build_academic_query_plan(
    query: str,
    query_intent: str,
    paper_ids: List[str] | None = None,
) -> Dict[str, Any]:
    """Build structured academic query plan for retrieval orchestration."""
    raw = (query or "").strip()
    family = classify_query_family(raw, query_intent)
    entities = _extract_entities(raw)
    decontextualized = _decontextualize_query(raw, entities)
    subqs = _sub_questions(family, decontextualized)
    rewrites = _fallback_rewrites(family, decontextualized)

    expected_evidence_types = ["text"]
    if family in {"compare", "numeric", "table"}:
        expected_evidence_types = ["text", "table"]
    if family == "figure":
        expected_evidence_types = ["text", "image"]

    planner_queries = plan_queries(raw, family)

    return {
        "query_type": family,
        "query_family": family,
        "decontextualized_query": decontextualized,
        "academic_entities": entities,
        "retrieval_facets": {
            "paper_ids": paper_ids or [],
            "paper_roles": PAPER_ROLE_HINTS,
            "expected_evidence_types": expected_evidence_types,
        },
        "sub_questions": subqs,
        "fallback_rewrites": rewrites,
        "expected_evidence_types": expected_evidence_types,
        "planner_queries": planner_queries,
        "planner_query_count": len(planner_queries),
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

    intent = classify_query_family(raw, query_intent)
    if intent == "compare":
        planned.append(f"{raw} 对比 差异 指标")
    elif intent == "evolution":
        planned.append(f"{raw} 时间线 演化 变化")
    elif intent in {"fact", "summary"}:
        planned.append(f"{raw} 关键结论 方法 结果")
    elif intent == "critique":
        planned.append(f"{raw} limitation weakness failure")
    elif intent == "limitation":
        planned.append(f"{raw} limitation boundary error")
    elif intent == "numeric":
        planned.append(f"{raw} metric value score table")
    elif intent == "figure":
        planned.append(f"{raw} figure caption visualization")
    elif intent == "table":
        planned.append(f"{raw} table row column metric")

    if any(token in raw.lower() for token in ["table", "figure", "图", "表"]):
        planned.append(f"{raw} table figure caption")

    deduped: List[str] = []
    for q in planned:
        q = q.strip()
        if q and q not in deduped:
            deduped.append(q)

    return deduped[:4]
