"""Unit tests for sparse lexical recall service."""

from app.core.bm25_service import SparseRecallService


def test_sparse_score_higher_for_term_match():
    service = SparseRecallService()

    query = "transformer attention"
    good_text = "This paper studies transformer architecture and attention mechanism."
    bad_text = "This paper studies graph diffusion over molecules."

    assert service.score(query, good_text) > service.score(query, bad_text)


def test_sparse_score_in_valid_range():
    service = SparseRecallService()

    value = service.score("query", "some candidate text")
    assert 0.0 <= value <= 1.0


def test_sparse_batch_scoring_matches_length():
    service = SparseRecallService()

    values = service.score_batch("vision model", ["vision", "language", "multimodal"])
    assert len(values) == 3
