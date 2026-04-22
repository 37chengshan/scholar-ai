from __future__ import annotations

from typing import Dict

from app.core.claim_schema import AbstainDecision, AnswerMode


class AbstentionPolicy:
    """Decide full/partial/abstain from claim verification and citation metrics."""

    def decide(
        self,
        *,
        claim_report: Dict,
        citation_report: Dict,
        answer_evidence_consistency: float,
    ) -> AbstainDecision:
        total = int(claim_report.get("totalClaims") or 0)
        supported = int(claim_report.get("supportedClaimCount") or 0)
        weak = int(claim_report.get("weaklySupportedClaimCount") or 0)
        unsupported = int(claim_report.get("unsupportedClaimCount") or 0)
        unsupported_rate = float(claim_report.get("unsupportedClaimRate") or 0.0)

        citation_count = int(citation_report.get("citation_count") or 0)
        matched_count = int(citation_report.get("matched_citation_count") or 0)
        citation_coverage = (matched_count / citation_count) if citation_count else 0.0

        if total == 0:
            return AbstainDecision(
                answer_mode=AnswerMode.abstain,
                abstained=True,
                abstain_reason="no_claims_extracted",
                unsupported_claim_rate=0.0,
                citation_coverage=round(citation_coverage, 4),
                answer_evidence_consistency=round(answer_evidence_consistency, 4),
            )

        if unsupported_rate > 0.5 or citation_coverage < 0.25:
            mode = AnswerMode.abstain
            reason = "insufficient_evidence"
        elif unsupported_rate > 0.15 or citation_coverage < 0.7 or answer_evidence_consistency < 0.4:
            mode = AnswerMode.partial
            reason = "partial_evidence"
        else:
            mode = AnswerMode.full
            reason = None

        return AbstainDecision(
            answer_mode=mode,
            abstained=mode == AnswerMode.abstain,
            abstain_reason=reason,
            unsupported_claim_rate=round(unsupported_rate, 4),
            citation_coverage=round(citation_coverage, 4),
            answer_evidence_consistency=round(answer_evidence_consistency, 4),
            supported_claim_count=supported,
            unsupported_claim_count=unsupported,
            weakly_supported_claim_count=weak,
        )


_abstention_policy: AbstentionPolicy | None = None


def get_abstention_policy() -> AbstentionPolicy:
    global _abstention_policy
    if _abstention_policy is None:
        _abstention_policy = AbstentionPolicy()
    return _abstention_policy
