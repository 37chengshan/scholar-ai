"""Test claim extraction from answer drafts."""

import pytest

from app.core.claim_extractor import ClaimExtractor


@pytest.fixture
def extractor() -> ClaimExtractor:
    return ClaimExtractor()


def test_extracts_claims_and_strips_citations(extractor: ClaimExtractor) -> None:
    draft = (
        "BERT is a transformer model with bidirectional pretraining [BERT, Introduction]. "
        "RoBERTa outperforms BERT on GLUE with higher accuracy [RoBERTa, Results]."
    )

    claims = extractor.extract(draft)

    assert len(claims) == 2
    assert claims[0].claim_type == "factual"
    assert claims[0].citations == ["[BERT, Introduction]"]
    assert "[BERT, Introduction]" not in claims[0].text
    assert claims[1].claim_type == "comparative"


def test_extracts_numeric_causal_and_limitation_claims(extractor: ClaimExtractor) -> None:
    draft = (
        "The model achieves 93.5% accuracy on SQuAD [Paper A, Results]. "
        "Because the encoder uses contrastive learning, retrieval quality improves [Paper A, Discussion]. "
        "A limitation is sensitivity to low-light conditions [Paper A, Limitation]."
    )

    claims = extractor.extract(draft)
    claim_types = [claim.claim_type for claim in claims]

    assert claim_types == ["numeric", "causal", "limitation"]


def test_ignores_empty_and_short_segments(extractor: ClaimExtractor) -> None:
    claims = extractor.extract("Short. Also short!   ")
    assert claims == []


def test_claim_ids_are_stable_and_unique(extractor: ClaimExtractor) -> None:
    draft = (
        "This first sentence is intentionally long enough to become a factual claim. "
        "This second sentence is also long enough to become another claim."
    )

    claims = extractor.extract(draft)

    assert [claim.claim_id for claim in claims] == ["claim-1", "claim-2"]
