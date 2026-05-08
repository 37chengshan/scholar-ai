from app.services.paper_display_metadata import (
    is_plausible_extracted_title,
    normalize_extracted_authors,
    sanitize_paper_display_metadata,
)


def test_sanitize_paper_display_metadata_rejects_fixture_like_values() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="142c2950-0a4a-4994-ba9f-28fd422b8caa",
        title="Test Paper - Page 1",
        authors=["This paper demonstrates PDF parsing", "parallel extraction."],
        year=None,
        venue=None,
        fallback_title="test_5_pages.pdf",
    )

    assert result["title"] == "test_5_pages"
    assert result["authors"] == []
    assert result["year"] is None
    assert result["venue"] is None


def test_sanitize_paper_display_metadata_uses_author_fallback_when_title_is_bad() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="paper-2",
        title="Unknown",
        authors=["Gaël Marmin", "parallel extraction."],
        year=2023,
        venue="NeurIPS",
    )

    assert result["title"] == "Paper by Gaël Marmin"
    assert result["authors"] == ["Gaël Marmin"]


def test_sanitize_paper_display_metadata_keeps_valid_academic_fields() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="paper-1",
        title="LIMA: Less Is More for Alignment",
        authors=["Gaël Marmin", "Tianle Li"],
        year=2023,
        venue="NeurIPS",
    )

    assert result == {
        "title": "LIMA: Less Is More for Alignment",
        "authors": ["Gaël Marmin", "Tianle Li"],
        "year": 2023,
        "venue": "NeurIPS",
    }


def test_low_level_normalizers_reject_bad_extracted_values() -> None:
    assert is_plausible_extracted_title("Test Paper - Page 1") is False
    assert normalize_extracted_authors(
        ["This paper demonstrates PDF parsing", "parallel extraction."]
    ) == []


def test_sanitize_paper_display_metadata_strips_page_suffix_from_real_titles() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="paper-3",
        title="Attention Is All You Need - Page 1",
        authors=["Ashish Vaswani"],
        year=2017,
        venue="NeurIPS",
    )

    assert result["title"] == "Attention Is All You Need"
    assert result["authors"] == ["Ashish Vaswani"]


def test_sanitize_paper_display_metadata_rejects_summary_sentence_titles() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="paper-4",
        title="The paper focuses on demonstrating techniques for PDF parsing and parallel extraction.",
        authors=[],
        year=None,
        venue=None,
        fallback_title="test_5_pages.pdf",
    )

    assert result["title"] == "test_5_pages"


def test_sanitize_paper_display_metadata_rejects_problem_statement_titles() -> None:
    result = sanitize_paper_display_metadata(
        paper_id="paper-5",
        title="Problem Addressed: Existing large language models rely on expensive alignment corpora.",
        authors=["Alice Zhang"],
        year=2024,
        venue="ICLR",
    )

    assert result["title"] == "Paper by Alice Zhang"
