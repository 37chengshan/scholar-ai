from __future__ import annotations

from app.rag_v3.schemas import AnswerContract, EvidencePack, EvidenceQualityScore


def build_answer_contract(pack: EvidencePack, quality: EvidenceQualityScore) -> AnswerContract:
    claims = []
    unsupported_claims: list[str] = []
    citations = []

    critical_supported = 0
    total_claims = 0

    for candidate in pack.candidates[:10]:
        claim_text = candidate.anchor_text or candidate.source_chunk_id
        support_status = "supported" if candidate.rerank_score >= 0.7 else "partially_supported"
        if candidate.rerank_score < 0.4:
            support_status = "unsupported"
            unsupported_claims.append(claim_text)

        total_claims += 1
        if candidate.rerank_score >= 0.7:
            critical_supported += 1

        claims.append(
            {
                "claim": claim_text,
                "support_status": support_status,
                "supporting_source_chunk_ids": [candidate.source_chunk_id],
                "citation_ids": [candidate.source_chunk_id],
            }
        )
        citations.append(candidate.source_chunk_id)

    citation_support_rate = 1.0 if citations else 0.0
    critical_claim_supported_rate = critical_supported / max(total_claims, 1)

    unsupported_count = sum(1 for c in claims if c["support_status"] == "unsupported")
    has_partial = any(c["support_status"] == "partially_supported" for c in claims)

    if critical_supported == 0:
        final_answer_mode = "abstain"
    elif unsupported_count > 0:
        final_answer_mode = "abstain"
    elif critical_claim_supported_rate >= 0.9 and citation_support_rate >= 0.9 and not has_partial:
        final_answer_mode = "full"
    else:
        final_answer_mode = "partial"

    return AnswerContract(
        answer_mode=final_answer_mode,
        claims=claims,
        unsupported_claims=unsupported_claims,
        missing_evidence=quality.missing_evidence_types,
        citations=sorted(set(citations)),
    )
