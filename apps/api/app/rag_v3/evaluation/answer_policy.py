from __future__ import annotations

from app.rag_v3.schemas import AnswerContract, EvidencePack, EvidenceQualityScore


def build_answer_contract(pack: EvidencePack, quality: EvidenceQualityScore) -> AnswerContract:
    claims = []
    unsupported_claims: list[str] = []
    citations: list[str] = []

    for candidate in pack.candidates[:10]:
        claim_text = candidate.anchor_text or candidate.source_chunk_id
        support_status = "supported" if candidate.rerank_score >= 0.6 else "partially_supported"
        if candidate.rerank_score < 0.3:
            support_status = "unsupported"
            unsupported_claims.append(claim_text)
        claims.append(
            {
                "claim": claim_text,
                "support_status": support_status,
                "supporting_source_chunk_ids": [candidate.source_chunk_id],
                "citation_ids": [candidate.source_chunk_id],
            }
        )
        citations.append(candidate.source_chunk_id)

    return AnswerContract(
        answer_mode=quality.answerability,
        claims=claims,
        unsupported_claims=unsupported_claims,
        missing_evidence=quality.missing_evidence_types,
        citations=sorted(set(citations)),
    )
