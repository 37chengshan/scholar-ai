"""Tests for ParseArtifact contract."""

from app.contracts.parse_artifact import (
    ParseMode,
    ParseQualityLevel,
    build_parse_artifact,
)


def test_parse_artifact_maps_pypdf_fallback_to_text_only() -> None:
    parse_result = {
        "markdown": "hello",
        "items": [{"type": "text", "text": "hello", "page": 1}],
        "page_count": 1,
        "metadata": {
            "parse_mode": "pypdf_fallback",
            "ocr_used": False,
            "parse_warnings": ["docling_parse_failed_fallback_to_pypdf"],
        },
    }

    artifact = build_parse_artifact(
        paper_id="v2-p-001",
        source_uri="papers/v2-p-001.pdf",
        parse_result=parse_result,
    )

    assert artifact.parse_mode == ParseMode.PYPDF_FALLBACK
    assert artifact.quality_level == ParseQualityLevel.TEXT_ONLY
    assert artifact.supports_tables is False
    assert artifact.supports_figures is False
    assert artifact.parse_id


def test_parse_artifact_maps_native_to_full() -> None:
    parse_result = {
        "markdown": "native",
        "items": [{"type": "text", "text": "native", "page": 2}],
        "page_count": 2,
        "metadata": {
            "parse_mode": "native",
            "ocr_used": False,
            "parse_warnings": [],
        },
    }

    artifact = build_parse_artifact(
        paper_id="v2-p-002",
        source_uri="papers/v2-p-002.pdf",
        parse_result=parse_result,
    )

    assert artifact.parse_mode == ParseMode.DOCLING_NATIVE
    assert artifact.quality_level == ParseQualityLevel.FULL
    assert artifact.supports_tables is True
    assert artifact.supports_figures is True
