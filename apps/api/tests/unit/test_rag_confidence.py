"""Unit tests for confidence calculation with strict retrieval contract."""

import os

# Minimal env guards for importing app modules in unit tests.
os.environ.setdefault("ZHIPU_API_KEY", "test-api-key")
os.environ.setdefault("ENVIRONMENT", "test")

from app.api.rag import calculate_confidence, normalize_source_contract


def test_confidence_zero_without_sources():
    assert calculate_confidence("Any answer", []) == 0.0


def test_confidence_prefers_higher_scores():
    answer = "This answer is supported by multiple high-quality sources."

    low_score_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.30, "page_num": 1, "text_preview": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.35, "page_num": 2, "text_preview": "b"},
    ]
    high_score_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.80, "page_num": 1, "text_preview": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.85, "page_num": 2, "text_preview": "b"},
    ]

    assert calculate_confidence(answer, high_score_sources) > calculate_confidence(
        answer, low_score_sources
    )


def test_confidence_rewards_evidence_diversity():
    answer = "A moderately detailed answer with references."

    single_location_sources = [
        {"paper_id": "p1", "section": "results", "score": 0.8, "page_num": 1, "text_preview": "a"},
        {"paper_id": "p1", "section": "results", "score": 0.79, "page_num": 2, "text_preview": "b"},
        {"paper_id": "p1", "section": "results", "score": 0.78, "page_num": 3, "text_preview": "c"},
    ]
    diverse_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.8, "page_num": 1, "text_preview": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.79, "page_num": 2, "text_preview": "b"},
        {"paper_id": "p3", "section": "results", "score": 0.78, "page_num": 3, "text_preview": "c"},
    ]

    assert calculate_confidence(answer, diverse_sources) > calculate_confidence(
        answer, single_location_sources
    )


def test_confidence_raises_when_score_missing():
    answer = "Missing score must fail under strict contract."
    sources = [
        {"paper_id": "p1", "page_num": 1, "text_preview": "sample"},
    ]

    try:
        calculate_confidence(answer, sources)
        assert False, "Expected ValueError for missing score"
    except ValueError as exc:
        assert "score" in str(exc)


def test_normalize_source_contract_keeps_canonical_fields():
    source = {
        "paper_id": "p1",
        "score": 0.91,
        "page_num": 8,
        "text_preview": "canonical",
        "content_preview": "legacy-preview",
    }

    normalized = normalize_source_contract(source)

    assert normalized["score"] == 0.91
    assert normalized["page_num"] == 8
    assert normalized["text_preview"] == "canonical"
    assert normalized["content_preview"] == "legacy-preview"


def test_normalize_source_contract_requires_canonical_fields():
    source = {
        "paper_id": "p2",
        "score": 0.66,
        "page_num": 4,
        "text_preview": "canonical content",
    }

    normalized = normalize_source_contract(source)

    assert normalized["score"] == 0.66
    assert normalized["page_num"] == 4
    assert normalized["text_preview"] == "canonical content"


def test_confidence_explain_contains_expected_dimensions():
    answer = "A grounded answer with multiple supporting sources and enough detail."
    sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.80, "page_num": 1, "text_preview": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.78, "page_num": 2, "text_preview": "b"},
    ]

    score, explain = calculate_confidence(answer, sources, with_explain=True)
    assert 0.0 < score <= 1.0
    assert "score_coverage" in explain
    assert "evidence_diversity" in explain
    assert "answer_support" in explain
    assert "weights" in explain
