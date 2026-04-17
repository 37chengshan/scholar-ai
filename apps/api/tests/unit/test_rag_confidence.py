"""Unit tests for PR8 confidence calculation in RAG API."""

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
        {"paper_id": "p1", "section": "intro", "score": 0.30},
        {"paper_id": "p2", "section": "method", "score": 0.35},
    ]
    high_score_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.80},
        {"paper_id": "p2", "section": "method", "score": 0.85},
    ]

    assert calculate_confidence(answer, high_score_sources) > calculate_confidence(
        answer, low_score_sources
    )


def test_confidence_rewards_evidence_diversity():
    answer = "A moderately detailed answer with references."

    single_location_sources = [
        {"paper_id": "p1", "section": "results", "score": 0.8},
        {"paper_id": "p1", "section": "results", "score": 0.79},
        {"paper_id": "p1", "section": "results", "score": 0.78},
    ]
    diverse_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.8},
        {"paper_id": "p2", "section": "method", "score": 0.79},
        {"paper_id": "p3", "section": "results", "score": 0.78},
    ]

    assert calculate_confidence(answer, diverse_sources) > calculate_confidence(
        answer, single_location_sources
    )


def test_confidence_accepts_legacy_similarity_field():
    answer = "Legacy source format still computes confidence."
    sources = [
        {"paper_id": "p1", "page": 1, "similarity": 0.72},
        {"paper_id": "p2", "page": 2, "similarity": 0.68},
    ]

    value = calculate_confidence(answer, sources)
    assert 0.0 < value <= 1.0


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


def test_normalize_source_contract_falls_back_to_legacy_aliases():
    source = {
        "paper_id": "p2",
        "similarity": 0.66,
        "page": 4,
        "content_preview": "legacy content",
    }

    normalized = normalize_source_contract(source)

    assert normalized["score"] == 0.66
    assert normalized["page_num"] == 4
    assert normalized["text_preview"] == "legacy content"


def test_confidence_uses_canonical_score_over_legacy_similarity():
    answer = "Confidence should use canonical score when both are present."
    canonical_sources = [{"paper_id": "p1", "score": 0.9, "similarity": 0.1}]
    legacy_only_sources = [{"paper_id": "p1", "similarity": 0.1}]

    assert calculate_confidence(answer, canonical_sources) > calculate_confidence(
        answer, legacy_only_sources
    )
