from __future__ import annotations

from typing import Any


FAILURE_BUCKETS = {
    "paper_miss",
    "section_miss",
    "candidate_pool_miss",
    "reranker_miss",
    "answer_verification_miss",
    "content_type_miss",
    "numeric_miss",
    "graph_miss",
    "citation_miss",
}


def classify_failure(record: dict[str, Any]) -> str:
    if float(record.get("paper_hit_rate", 0.0)) <= 0.0:
        return "paper_miss"
    if float(record.get("section_hit_rate", 0.0)) <= 0.0:
        return "section_miss"
    if float(record.get("candidate_pool_oracle_recall_at_100", 0.0)) < 0.6:
        return "candidate_pool_miss"
    if float(record.get("rerank_loss", 0.0)) > 0.05:
        return "reranker_miss"
    if float(record.get("answer_evidence_consistency", 0.0)) < 0.55:
        return "answer_verification_miss"
    if float(record.get("content_type_match_score", 0.0)) < 0.5:
        return "content_type_miss"
    if float(record.get("numeric_hit_at_20", 0.0)) < 0.6:
        return "numeric_miss"
    if float(record.get("cross_paper_coverage", 0.0)) < 0.7:
        return "graph_miss"
    if float(record.get("citation_coverage", 0.0)) < 0.75:
        return "citation_miss"
    return "candidate_pool_miss"
