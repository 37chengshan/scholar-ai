from app.core.claim_schema import AnswerClaim
from app.rag_v3.schemas import EvidenceBlock
from app.services.truthfulness_service import get_truthfulness_service


def test_truthfulness_service_builds_four_level_report() -> None:
    report = get_truthfulness_service().evaluate_claims(
        claims=[
            AnswerClaim(claim_id="c1", text="Method A improves F1 on SQuAD", claim_type="numeric", citations=[]),
            AnswerClaim(
                claim_id="c2",
                text="Method A uses a sparse encoder with retrieval augmentation and calibration",
                claim_type="factual",
                citations=[],
            ),
            AnswerClaim(
                claim_id="c3",
                text="Method A uses a sparse encoder with curriculum regularization, long context calibration, and staged distillation for retrieval",
                claim_type="factual",
                citations=[],
            ),
            AnswerClaim(
                claim_id="c4",
                text="Human experts remove every legal compliance burden in downstream auditing",
                claim_type="causal",
                citations=[],
            ),
        ],
        evidence_blocks=[
            EvidenceBlock(
                evidence_id="chunk-1",
                paper_id="paper-1",
                source_chunk_id="chunk-1",
                text="Method A improves F1 on SQuAD and boosts retrieval performance in evaluation.",
            ),
            EvidenceBlock(
                evidence_id="chunk-2",
                paper_id="paper-1",
                source_chunk_id="chunk-2",
                text="Method A uses an encoder with sparse retrieval augmentation.",
            )
        ],
    )

    assert report["totalClaims"] == 4
    assert report["supportedClaimCount"] >= 1
    assert report["unsupportedClaimCount"] == 1
    assert report["weaklySupportedClaimCount"] + report["partiallySupportedClaimCount"] >= 1
    assert report["summary"]["answer_mode"] == "abstain"
    assert report["summary"]["verifier_backend"] == "rarr_cove_scifact_lite"
    assert report["summary"]["unsupported_claim_rate"] == report["unsupportedClaimRate"]


def test_truthfulness_service_repair_claim_returns_hint() -> None:
    result = get_truthfulness_service().repair_claim(
        claim_text="Method A improves F1 on SQuAD",
        claim_id="c1",
        claim_type="numeric",
        evidence_blocks=[
            EvidenceBlock(
                evidence_id="chunk-1",
                paper_id="paper-1",
                source_chunk_id="chunk-1",
                text="Method A improves F1 on SQuAD in evaluation.",
            )
        ],
    )

    assert result["support_level"] == "supported"
    assert result["repairable"] is False
