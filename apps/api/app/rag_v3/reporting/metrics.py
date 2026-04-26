from __future__ import annotations

from typing import Any

REQUIRED_V3_METRICS = {
    "paper_hit_at_10",
    "section_hit_at_10",
    "candidate_pool_oracle_recall_at_100",
    "exact_recall_at_10",
    "rerank_loss",
    "table_hit_at_20",
    "figure_hit_at_20",
    "numeric_hit_at_20",
    "citation_coverage",
    "unsupported_claim_rate",
    "answer_evidence_consistency",
}


def aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    if not records:
        return {metric: 0.0 for metric in REQUIRED_V3_METRICS}

    def _avg(key: str) -> float:
        values = [float(item.get(key, 0.0)) for item in records]
        return round(sum(values) / max(len(values), 1), 4)

    return {
        "paper_hit_at_10": _avg("paper_hit_at_10"),
        "section_hit_at_10": _avg("section_hit_at_10"),
        "candidate_pool_oracle_recall_at_100": _avg("candidate_pool_oracle_recall_at_100"),
        "exact_recall_at_10": _avg("exact_recall_at_10"),
        "rerank_loss": _avg("rerank_loss"),
        "table_hit_at_20": _avg("table_hit_at_20"),
        "figure_hit_at_20": _avg("figure_hit_at_20"),
        "numeric_hit_at_20": _avg("numeric_hit_at_20"),
        "citation_coverage": _avg("citation_coverage"),
        "unsupported_claim_rate": _avg("unsupported_claim_rate"),
        "answer_evidence_consistency": _avg("answer_evidence_consistency"),
    }
