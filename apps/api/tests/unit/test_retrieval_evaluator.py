from app.core.retrieval_evaluator import RetrievalEvaluator


def test_evaluator_marks_weak_when_scores_low_and_coverage_narrow() -> None:
    evaluator = RetrievalEvaluator()
    chunks = [
        {
            "paper_id": "paper-a",
            "section_path": "Introduction",
            "score": 0.21,
            "content_type": "text",
        },
        {
            "paper_id": "paper-a",
            "section_path": "Introduction",
            "score": 0.18,
            "content_type": "text",
        },
    ]

    report = evaluator.evaluate(
        query_family="compare",
        chunks=chunks,
        expected_evidence_types=["text", "table"],
        paper_ids=["paper-a", "paper-b", "paper-c"],
        graph_candidates=[],
        top_k=5,
    )

    assert report["is_weak"] is True
    assert "low_score_coverage" in report["weak_reasons"]
    assert "insufficient_cross_paper_coverage" in report["weak_reasons"]
    assert "missing_expected_evidence_type:table" in report["weak_reasons"]
    assert report["trigger_citation_expansion"] is True


def test_evaluator_marks_strong_when_diverse_and_type_covered() -> None:
    evaluator = RetrievalEvaluator()
    chunks = [
        {
            "paper_id": "paper-a",
            "section_path": "Results",
            "score": 0.91,
            "content_type": "text",
        },
        {
            "paper_id": "paper-b",
            "section_path": "Table 2",
            "score": 0.84,
            "content_type": "table",
        },
    ]

    report = evaluator.evaluate(
        query_family="compare",
        chunks=chunks,
        expected_evidence_types=["text", "table"],
        paper_ids=["paper-a", "paper-b"],
        graph_candidates=[{"paper_id": "paper-b", "relation": "compares_against_baseline"}],
        top_k=5,
    )

    assert report["is_weak"] is False
    assert report["trigger_citation_expansion"] is False
    assert report["metrics"]["cross_paper_coverage"] >= 1.0
