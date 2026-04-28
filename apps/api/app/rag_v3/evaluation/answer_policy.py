from __future__ import annotations

from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.rag_v3.schemas import AnswerContract, EvidencePack, EvidenceQualityScore


def build_answer_contract(pack: EvidencePack, quality: EvidenceQualityScore) -> AnswerContract:
    claims = []
    unsupported_claims: list[str] = []
    citations = []
    evidence_blocks = []

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

        source_payload = get_evidence_source_payload(candidate.source_chunk_id) or {}
        citation_jump_url = source_payload.get("citation_jump_url") or build_citation_jump_url(
            paper_id=candidate.paper_id,
            source_chunk_id=candidate.source_chunk_id,
        )

        claims.append(
            {
                "claim": claim_text,
                "support_status": support_status,
                "supporting_source_chunk_ids": [candidate.source_chunk_id],
                "citation_ids": [candidate.source_chunk_id],
            }
        )
        citations.append(
            {
                "paper_id": candidate.paper_id,
                "source_chunk_id": candidate.source_chunk_id,
                "page_num": source_payload.get("page_num"),
                "section_path": source_payload.get("section_path") or candidate.section_id,
                "title": candidate.paper_id,
                "anchor_text": candidate.anchor_text,
                "text_preview": candidate.anchor_text,
                "score": candidate.rerank_score,
                "content_type": candidate.content_type,
                "citation_jump_url": citation_jump_url,
            }
        )
        evidence_blocks.append(
            {
                "evidence_id": candidate.source_chunk_id,
                "source_type": "paper",
                "paper_id": candidate.paper_id,
                "source_chunk_id": candidate.source_chunk_id,
                "page_num": source_payload.get("page_num"),
                "section_path": source_payload.get("section_path") or candidate.section_id,
                "content_type": candidate.content_type,
                "text": candidate.anchor_text,
                "score": candidate.rerank_score,
                "rerank_score": candidate.rerank_score,
                "support_status": support_status,
                "citation_jump_url": citation_jump_url,
            }
        )

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
        response_type="rag",
        answer_mode=final_answer_mode,
        answer="",
        claims=claims,
        unsupported_claims=unsupported_claims,
        missing_evidence=quality.missing_evidence_types,
        citations=citations,
        evidence_blocks=evidence_blocks,
        quality={
            "citation_coverage": quality.citation_support_score,
            "unsupported_claim_rate": len(unsupported_claims) / max(len(claims), 1),
            "answer_evidence_consistency": quality.evidence_relevance_score,
            "fallback_used": False,
            "fallback_reason": None,
        },
    )
