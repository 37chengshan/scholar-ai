from __future__ import annotations

from app.rag_v3.prompt_builder import (
    _build_summary_display_text,
    _clean_display_evidence_text,
    build_summary_display_text,
    clean_display_evidence_text,
)


def test_clean_display_evidence_text_public_api_matches_compat_helper() -> None:
    raw = "[Paper Summary: p-1]\nA Test Paper\nGLYPH<12> Method result"

    assert clean_display_evidence_text(raw, title="A Test Paper") == _clean_display_evidence_text(
        raw,
        title="A Test Paper",
    )
    assert clean_display_evidence_text(raw, title="A Test Paper") == "Method result"


def test_build_summary_display_text_public_api_matches_compat_helper() -> None:
    summary = {
        "title": "A Test Paper",
        "paper_summary": "[Paper Summary: p-1]\nA Test Paper\nThe method is grounded.",
        "abstract": "unused",
    }

    assert build_summary_display_text(summary) == _build_summary_display_text(summary)
    assert build_summary_display_text(summary) == "The method is grounded."
