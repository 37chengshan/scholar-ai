from app.core.claim_schema import AnswerClaim
from app.core.claim_verifier import ClaimVerifier


def test_claim_verifier_scores_supported_weak_and_unsupported_claims() -> None:
    verifier = ClaimVerifier()
    claims = [
        AnswerClaim(claim_id="claim-1", text="Method A improves F1 on SQuAD", claim_type="numeric"),
        AnswerClaim(
            claim_id="claim-2",
            text="Method A uses a sparse encoder with retrieval augmentation, calibration, confidence gating, multi-stage routing, and deferred fusion",
            claim_type="factual",
        ),
        AnswerClaim(
            claim_id="claim-3",
            text="Method A uses a sparse encoder with curriculum regularization, long context calibration, and staged distillation for retrieval",
            claim_type="factual",
        ),
        AnswerClaim(
            claim_id="claim-4",
            text="Human experts remove every legal compliance burden in downstream auditing",
            claim_type="causal",
        ),
    ]
    sources = [
        {
            "source_id": "bundle-1",
            "text": "Method A improves F1 on SQuAD and boosts retrieval performance in evaluation.",
            "anchor_text": "Method A improves F1 on SQuAD",
        },
        {
            "source_id": "bundle-2",
            "text": "Method A uses an encoder with sparse retrieval augmentation.",
            "anchor_text": "uses an encoder with sparse retrieval augmentation",
        },
    ]

    results = verifier.verify(claims, sources)
    report = verifier.build_report(results)

    assert results[0].support_level.value == "supported"
    assert results[1].support_level.value == "weakly_supported"
    assert results[2].support_level.value in {"weakly_supported", "partially_supported"}
    assert results[3].support_level.value == "unsupported"
    assert report["verifierBackend"] == "rarr_cove_scifact_lite"
    assert report["supportedClaimCount"] == 1
    assert report["weaklySupportedClaimCount"] + report["partiallySupportedClaimCount"] == 2
    assert report["unsupportedClaimCount"] == 1
    assert report["unsupportedClaimRate"] == 0.25


def test_claim_verifier_handles_empty_claims() -> None:
    verifier = ClaimVerifier()
    assert verifier.verify([], [{"source_id": "bundle-1", "text": "evidence"}]) == []
