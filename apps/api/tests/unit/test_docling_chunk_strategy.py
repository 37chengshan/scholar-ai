"""Tests for PR7 docling chunk strategy and parse metadata routing."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.core.docling_service import DoclingParser, ParserConfig
from app.core.imrad_extractor import get_section_chunk_params


class TestChunkStrategy:
    """Validate section-adaptive chunk sizing behavior."""

    def test_section_specific_chunk_size_used_without_override(self):
        parser = DoclingParser.__new__(DoclingParser)

        items = [
            {
                "type": "text",
                "text": "This is a methods paragraph with enough words to test adaptive chunk logic.",
                "page": 2,
            }
        ]
        section_spans = {
            "methods": {"page_start": 2, "page_end": 2, "confidence": 0.9}
        }

        with patch.object(
            parser,
            "_merge_small_chunks_with_overlap",
            side_effect=lambda chunks, **_: chunks,
        ):
            chunks = DoclingParser.chunk_by_semantic(
                parser,
                items=items,
                paper_id="paper-1",
                section_spans=section_spans,
            )

        assert len(chunks) == 1
        assert chunks[0]["section"] == "methods"
        assert chunks[0]["adaptive_size"] == get_section_chunk_params("methods")["size"]

    def test_explicit_chunk_override_takes_priority(self):
        parser = DoclingParser.__new__(DoclingParser)

        items = [
            {
                "type": "text",
                "text": "This is another methods paragraph that should respect explicit chunk override.",
                "page": 3,
            }
        ]
        section_spans = {
            "methods": {"page_start": 3, "page_end": 3, "confidence": 0.9}
        }

        with patch.object(
            parser,
            "_merge_small_chunks_with_overlap",
            side_effect=lambda chunks, **_: chunks,
        ):
            chunks = DoclingParser.chunk_by_semantic(
                parser,
                items=items,
                paper_id="paper-2",
                section_spans=section_spans,
                chunk_size=700,
            )

        assert len(chunks) == 1
        assert chunks[0]["adaptive_size"] == 700


class TestParseMetadata:
    """Validate parse mode tracking and OCR fallback metadata."""

    @pytest.mark.asyncio
    async def test_parse_pdf_records_ocr_fallback_metadata(self):
        parser = DoclingParser(config=ParserConfig(do_ocr=True))

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test")
            tmp_path = tmp.name

        native_doc = Mock()
        native_doc.export_to_markdown.return_value = "x"
        native_doc.iterate_items.return_value = []
        native_doc.pages = [Mock(), Mock()]
        native_doc.name = "native.pdf"

        ocr_doc = Mock()
        ocr_doc.export_to_markdown.return_value = "This is OCR extracted text with enough density to avoid retries."
        ocr_doc.iterate_items.return_value = []
        ocr_doc.pages = [Mock(), Mock()]
        ocr_doc.name = "ocr.pdf"

        native_result = Mock(document=native_doc)
        ocr_result = Mock(document=ocr_doc)

        with patch.object(parser.native_converter, "convert", return_value=native_result), patch.object(
            parser.ocr_converter, "convert", return_value=ocr_result
        ):
            result = await parser.parse_pdf(tmp_path)

        metadata = result["metadata"]
        assert metadata["parse_mode"] == "ocr_fallback"
        assert metadata["ocr_used"] is True
        assert "low_text_density_retry_with_ocr" in metadata["parse_warnings"]
        assert metadata["chunk_strategy"]["mode"] == "section_adaptive"

        Path(tmp_path).unlink(missing_ok=True)
