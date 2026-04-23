from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass(frozen=True)
class RetrievalEvaluatorThresholds:
    score_coverage_min: float = 0.45
    diversity_min: float = 0.35
    concentration_max: float = 0.8
    cross_paper_min: float = 0.5


class RetrievalEvaluator:
    """Evaluate first-pass retrieval quality before synthesis.

    Iteration 3 policy:
    - If evidence is weak, trigger iterative retrieval instead of direct synthesis.
    - Weakness is decided by score coverage, diversity, concentration, cross-paper
      coverage, expected evidence-type coverage, and citation expansion need.
    """

    def __init__(self, thresholds: RetrievalEvaluatorThresholds | None = None):
        self.thresholds = thresholds or RetrievalEvaluatorThresholds()

    def evaluate(
        self,
        *,
        query_family: str,
        chunks: Sequence[Dict[str, Any]],
        expected_evidence_types: Sequence[str],
        paper_ids: Sequence[str],
        graph_candidates: Sequence[Dict[str, Any]],
        top_k: int = 8,
    ) -> Dict[str, Any]:
        ranked = sorted(list(chunks), key=lambda item: float(item.get("score") or 0.0), reverse=True)
        top = ranked[: max(top_k, 1)]

        score_coverage = self._score_coverage(top)
        evidence_diversity = self._evidence_diversity(top)
        paper_concentration = self._paper_concentration(top)
        cross_paper_coverage = self._cross_paper_coverage(top, paper_ids)
        expected_hits, missing_expected_types = self._expected_type_hits(top, expected_evidence_types)

        weak_reasons: List[str] = []
        if score_coverage < self.thresholds.score_coverage_min:
            weak_reasons.append("low_score_coverage")
        if evidence_diversity < self.thresholds.diversity_min:
            weak_reasons.append("low_evidence_diversity")
        if paper_concentration > self.thresholds.concentration_max:
            weak_reasons.append("evidence_over_concentrated")

        family = (query_family or "fact").lower()
        needs_cross_paper = family in {"compare", "evolution", "survey"}
        if needs_cross_paper and cross_paper_coverage < self.thresholds.cross_paper_min:
            weak_reasons.append("insufficient_cross_paper_coverage")

        for expected_type in missing_expected_types:
            weak_reasons.append(f"missing_expected_evidence_type:{expected_type}")

        trigger_citation_expansion = self._should_trigger_citation_expansion(
            family,
            cross_paper_coverage,
            graph_candidates,
        )
        if trigger_citation_expansion:
            weak_reasons.append("citation_expansion_recommended")

        is_weak = len(weak_reasons) > 0

        return {
            "is_weak": is_weak,
            "weak_reasons": weak_reasons,
            "trigger_citation_expansion": trigger_citation_expansion,
            "missing_expected_evidence_types": missing_expected_types,
            "metrics": {
                "score_coverage": score_coverage,
                "evidence_diversity": evidence_diversity,
                "paper_concentration": paper_concentration,
                "cross_paper_coverage": cross_paper_coverage,
                "expected_evidence_type_hit_rate": expected_hits,
                "top_k_considered": len(top),
            },
        }

    @staticmethod
    def _score_coverage(chunks: Sequence[Dict[str, Any]]) -> float:
        if not chunks:
            return 0.0
        scores = [max(0.0, min(float(item.get("score") or 0.0), 1.0)) for item in chunks]
        return round(sum(scores) / len(scores), 4)

    @staticmethod
    def _evidence_diversity(chunks: Sequence[Dict[str, Any]]) -> float:
        if not chunks:
            return 0.0
        keys = set()
        for item in chunks:
            paper_id = str(item.get("paper_id") or "unknown")
            section = str(item.get("section_path") or item.get("section") or item.get("page_num") or "unknown")
            keys.add((paper_id, section))
        return round(min(len(keys) / max(len(chunks), 1), 1.0), 4)

    @staticmethod
    def _paper_concentration(chunks: Sequence[Dict[str, Any]]) -> float:
        if not chunks:
            return 1.0
        counter: Dict[str, int] = {}
        for item in chunks:
            paper_id = str(item.get("paper_id") or "unknown")
            counter[paper_id] = counter.get(paper_id, 0) + 1
        max_count = max(counter.values()) if counter else 0
        return round(max_count / max(len(chunks), 1), 4)

    @staticmethod
    def _cross_paper_coverage(chunks: Sequence[Dict[str, Any]], paper_ids: Sequence[str]) -> float:
        target = len(set(str(p) for p in (paper_ids or []) if p))
        if target <= 0:
            target = 2
        seen = {str(item.get("paper_id")) for item in chunks if item.get("paper_id")}
        return round(min(len(seen) / max(target, 1), 1.0), 4)

    @staticmethod
    def _expected_type_hits(
        chunks: Sequence[Dict[str, Any]],
        expected_types: Sequence[str],
    ) -> tuple[float, List[str]]:
        normalized_expected = [str(item).lower() for item in (expected_types or []) if item]
        if not normalized_expected:
            return 1.0, []

        seen = set()
        for item in chunks:
            content_type = str(item.get("content_type") or item.get("content_subtype") or "text").lower()
            if content_type.startswith("figure"):
                content_type = "image"
            seen.add(content_type)

        missing = [item for item in normalized_expected if item not in seen]
        hit_rate = 1.0 - (len(missing) / len(normalized_expected))
        return round(max(0.0, hit_rate), 4), missing

    @staticmethod
    def _should_trigger_citation_expansion(
        query_family: str,
        cross_paper_coverage: float,
        graph_candidates: Sequence[Dict[str, Any]],
    ) -> bool:
        if query_family not in {"compare", "evolution", "survey", "numeric"}:
            return False
        if graph_candidates:
            return cross_paper_coverage < 0.35
        return cross_paper_coverage < 0.8
