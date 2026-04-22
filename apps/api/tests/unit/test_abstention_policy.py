from app.core.abstention_policy import AbstentionPolicy


def test_abstention_policy_returns_full_when_evidence_is_strong() -> None:
    decision = AbstentionPolicy().decide(
        claim_report={
            "totalClaims": 3,
            "supportedClaimCount": 3,
            "weaklySupportedClaimCount": 0,
            "unsupportedClaimCount": 0,
            "unsupportedClaimRate": 0.0,
        },
        citation_report={"citation_count": 3, "matched_citation_count": 3},
        answer_evidence_consistency=0.82,
    )

    assert decision.answer_mode.value == "full"
    assert decision.abstained is False
    assert decision.abstain_reason is None


def test_abstention_policy_returns_partial_when_evidence_is_mixed() -> None:
    decision = AbstentionPolicy().decide(
        claim_report={
            "totalClaims": 4,
            "supportedClaimCount": 2,
            "weaklySupportedClaimCount": 1,
            "unsupportedClaimCount": 1,
            "unsupportedClaimRate": 0.25,
        },
        citation_report={"citation_count": 4, "matched_citation_count": 3},
        answer_evidence_consistency=0.55,
    )

    assert decision.answer_mode.value == "partial"
    assert decision.abstained is False
    assert decision.abstain_reason == "partial_evidence"


def test_abstention_policy_returns_abstain_for_no_claims() -> None:
    decision = AbstentionPolicy().decide(
        claim_report={"totalClaims": 0},
        citation_report={"citation_count": 0, "matched_citation_count": 0},
        answer_evidence_consistency=0.0,
    )

    assert decision.answer_mode.value == "abstain"
    assert decision.abstained is True
    assert decision.abstain_reason == "no_claims_extracted"
