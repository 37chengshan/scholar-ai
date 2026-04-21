"""Unit tests for retrieval scoring helpers."""

from app.core.retrieval_scoring import RetrievalScoreBreakdown, RetrievalScoringService


def test_score_candidate_combines_vector_and_sparse_scores():
    service = RetrievalScoringService(vector_weight=0.75, sparse_weight=0.25)

    scored = service.score_candidate(
        query="transformer attention",
        candidate_text="transformer attention mechanisms improve long-context modeling",
        raw_vector_score=0.8,
    )

    assert isinstance(scored, RetrievalScoreBreakdown)
    assert scored.vector_score == 0.8
    assert 0.0 <= scored.sparse_score <= 1.0
    assert scored.hybrid_score >= 0.6


def test_apply_reranker_scores_prefers_structured_document_match():
    service = RetrievalScoringService()
    results = [
        {
            "paper_id": "paper-1",
            "text": "content 0",
            "title": "Paper One",
            "paper_title": "Paper One",
            "section": "Methods",
            "page_num": 1,
            "content_type": "text",
        },
        {
            "paper_id": "paper-2",
            "text": "content 1",
            "paper_title": "Paper Two",
            "section": "Results",
            "page_num": 2,
            "content_type": "text",
        },
    ]

    reranked = [
        {
            "document": (
                "title: Paper Two\n"
                "section: Results\n"
                "page_num: 2\n"
                "content_type: text\n"
                "text: content 1"
            ),
            "score": 0.91,
        },
        {"document": "content 0", "score": 0.3},
    ]

    reordered = service.apply_reranker_scores(results, reranked)

    assert reordered[0]["paper_id"] == "paper-2"
    assert reordered[0]["reranker_score"] == 0.91
    assert reordered[1]["reranker_score"] == 0.3