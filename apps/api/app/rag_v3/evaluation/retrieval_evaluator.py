from __future__ import annotations

from typing import Sequence

from app.rag_v3.schemas import EvidencePack, EvidenceQualityScore


def evaluate_evidence_pack(pack: EvidencePack) -> EvidenceQualityScore:
    if not pack.candidates:
        return EvidenceQualityScore(
            query_id=pack.query_id,
            answerability="abstain",
            paper_coverage_score=0.0,
            section_match_score=0.0,
            content_type_match_score=0.0,
            evidence_relevance_score=0.0,
            citation_support_score=0.0,
            missing_evidence_types=["text"],
            recommended_action="abstain",
        )

    papers = {item.paper_id for item in pack.candidates if item.paper_id}
    sections = {item.section_id for item in pack.candidates if item.section_id}
    content_types = {item.content_type for item in pack.candidates if item.content_type}
    top_scores = [item.rerank_score for item in pack.candidates[:10]]

    paper_coverage_score = min(len(papers) / 3.0, 1.0)
    section_match_score = min(len(sections) / 5.0, 1.0)
    content_type_match_score = min(len(content_types) / 2.0, 1.0)
    evidence_relevance_score = sum(top_scores) / max(len(top_scores), 1)
    citation_support_score = min(len(pack.candidates) / 10.0, 1.0)

    final_score = (
        0.25 * paper_coverage_score
        + 0.2 * section_match_score
        + 0.2 * content_type_match_score
        + 0.25 * evidence_relevance_score
        + 0.1 * citation_support_score
    )

    answerability = _to_answerability(final_score)
    recommended_action = _to_action(answerability)

    return EvidenceQualityScore(
        query_id=pack.query_id,
        answerability=answerability,
        paper_coverage_score=round(paper_coverage_score, 4),
        section_match_score=round(section_match_score, 4),
        content_type_match_score=round(content_type_match_score, 4),
        evidence_relevance_score=round(evidence_relevance_score, 4),
        citation_support_score=round(citation_support_score, 4),
        missing_evidence_types=_missing_types(content_types),
        recommended_action=recommended_action,
    )


def _to_answerability(score: float) -> str:
    if score >= 0.75:
        return "full"
    if score >= 0.45:
        return "partial"
    return "abstain"


def _to_action(answerability: str) -> str:
    if answerability == "full":
        return "answer"
    if answerability == "partial":
        return "retry_sparse"
    return "abstain"


def _missing_types(content_types: Sequence[str]) -> list[str]:
    normalized = {str(item).lower() for item in content_types}
    required = {"text"}
    return sorted(required - normalized)
