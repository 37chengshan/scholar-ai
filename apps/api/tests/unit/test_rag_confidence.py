"""Unit tests for confidence calculation with strict retrieval contract."""

import os
import json
from pathlib import Path

# Minimal env guards for importing app modules in unit tests.
os.environ.setdefault("ZHIPU_API_KEY", "test-api-key")
os.environ.setdefault("ENVIRONMENT", "test")

from app.api.rag import calculate_confidence, normalize_source_contract


def test_confidence_zero_without_sources():
    assert calculate_confidence("Any answer", []) == 0.0


def test_confidence_prefers_higher_scores():
    answer = "This answer is supported by multiple high-quality sources."

    low_score_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.30, "page_num": 1, "text_preview": "a", "source_id": "s1", "section_path": "intro", "content_subtype": "paragraph", "anchor_text": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.35, "page_num": 2, "text_preview": "b", "source_id": "s2", "section_path": "method", "content_subtype": "paragraph", "anchor_text": "b"},
    ]
    high_score_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.80, "page_num": 1, "text_preview": "a", "source_id": "s1", "section_path": "intro", "content_subtype": "paragraph", "anchor_text": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.85, "page_num": 2, "text_preview": "b", "source_id": "s2", "section_path": "method", "content_subtype": "paragraph", "anchor_text": "b"},
    ]

    assert calculate_confidence(answer, high_score_sources) > calculate_confidence(
        answer, low_score_sources
    )


def test_confidence_rewards_evidence_diversity():
    answer = "A moderately detailed answer with references."

    single_location_sources = [
        {"paper_id": "p1", "section": "results", "score": 0.8, "page_num": 1, "text_preview": "a", "source_id": "s1", "section_path": "results", "content_subtype": "paragraph", "anchor_text": "a"},
        {"paper_id": "p1", "section": "results", "score": 0.79, "page_num": 2, "text_preview": "b", "source_id": "s2", "section_path": "results", "content_subtype": "paragraph", "anchor_text": "b"},
        {"paper_id": "p1", "section": "results", "score": 0.78, "page_num": 3, "text_preview": "c", "source_id": "s3", "section_path": "results", "content_subtype": "paragraph", "anchor_text": "c"},
    ]
    diverse_sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.8, "page_num": 1, "text_preview": "a", "source_id": "s1", "section_path": "intro", "content_subtype": "paragraph", "anchor_text": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.79, "page_num": 2, "text_preview": "b", "source_id": "s2", "section_path": "method", "content_subtype": "paragraph", "anchor_text": "b"},
        {"paper_id": "p3", "section": "results", "score": 0.78, "page_num": 3, "text_preview": "c", "source_id": "s3", "section_path": "results", "content_subtype": "paragraph", "anchor_text": "c"},
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
        "source_id": "s1",
        "section_path": "results",
        "content_subtype": "paragraph",
        "anchor_text": "canonical",
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
        "source_id": "s1",
        "section_path": "intro",
        "content_subtype": "paragraph",
        "anchor_text": "canonical content",
    }

    normalized = normalize_source_contract(source)

    assert normalized["score"] == 0.66
    assert normalized["page_num"] == 4
    assert normalized["text_preview"] == "canonical content"


def test_confidence_explain_contains_expected_dimensions():
    answer = "A grounded answer with multiple supporting sources and enough detail."
    sources = [
        {"paper_id": "p1", "section": "intro", "score": 0.80, "page_num": 1, "text_preview": "a", "source_id": "s1", "section_path": "intro", "content_subtype": "paragraph", "anchor_text": "a"},
        {"paper_id": "p2", "section": "method", "score": 0.78, "page_num": 2, "text_preview": "b", "source_id": "s2", "section_path": "method", "content_subtype": "paragraph", "anchor_text": "b"},
    ]

    score, explain, answer_consistency, low_reasons = calculate_confidence(
        answer, sources, with_explain=True
    )
    assert 0.0 < score <= 1.0
    assert "score_coverage" in explain
    assert "evidence_diversity" in explain
    assert "answer_support" in explain
    assert "answerEvidenceConsistency" in explain
    assert "weights" in explain
    assert 0.0 <= answer_consistency <= 1.0
    assert isinstance(low_reasons, list)


def test_confidence_low_reason_retrieval_weak():
    answer = "short answer"
    weak_sources = [
        {
            "paper_id": "p1",
            "score": 0.1,
            "page_num": 1,
            "text_preview": "random context",
            "source_id": "s1",
            "section_path": "intro",
            "content_subtype": "paragraph",
            "anchor_text": "random context",
        }
    ]

    _score, _explain, _consistency, reasons = calculate_confidence(
        answer, weak_sources, with_explain=True
    )
    assert "retrieval_weak" in reasons


def test_vnext_freeze_eval_fixture_has_20_items_and_required_fields():
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "rag"
        / "vnext_freeze_eval_set.json"
    )
    assert fixture_path.exists()

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) == 20

    required_item_keys = {
        "id",
        "query",
        "paper_ids",
        "expected_citation_fields",
        "expected_low_confidence_reason",
        "notes",
    }
    required_citation_fields = {
        "paper_id",
        "source_id",
        "page_num",
        "section_path",
        "anchor_text",
        "text_preview",
    }

    for item in payload:
        assert required_item_keys.issubset(item.keys())
        assert required_citation_fields.issubset(set(item["expected_citation_fields"]))
