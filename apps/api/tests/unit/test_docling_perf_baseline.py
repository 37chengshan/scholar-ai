"""Perf baseline smoke tests for born-digital vs scanned OCR fallback path."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.core.docling_service import DoclingParser


def test_should_retry_with_ocr_for_low_text_density(monkeypatch):
    parser = DoclingParser.__new__(DoclingParser)
    parser.config = MagicMock(ocr_retry_min_chars_per_page=80)

    markdown = "x" * 20
    page_count = 1

    assert parser._should_retry_with_ocr(markdown, page_count) is True


def test_no_retry_for_high_text_density(monkeypatch):
    parser = DoclingParser.__new__(DoclingParser)
    parser.config = MagicMock(ocr_retry_min_chars_per_page=80)

    markdown = "x" * 1000
    page_count = 1

    assert parser._should_retry_with_ocr(markdown, page_count) is False
