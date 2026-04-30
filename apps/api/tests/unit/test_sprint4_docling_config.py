"""Tests for Sprint 4 Task 1: Docling Configuration

Tests for configurable Docling parser options:
- ParserConfig class with defaults
- OCR enabled by default (was False)
- Image/table extraction enabled by default
- force_ocr override for scanned PDFs
- File size limit enforcement
- Timeout protection

Per Sprint 4 Task 1 acceptance criteria:
✅ DoclingParser初始化参数可配置
✅ 默认启用 OCR
✅ 前端 forceOcr 参数可覆盖默认配置
"""

import pytest
import os
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from app.core.docling_service import (
    DoclingParser,
    ParserConfig,
    FileTooLargeError,
    ParseTimeoutError,
    PageLimitError,
    get_docling_parser,
)


class TestParserConfig:
    """Tests for ParserConfig dataclass."""

    def test_parser_config_defaults(self):
        """Test ParserConfig has correct defaults per Sprint 4."""
        config = ParserConfig()

        # Per PR7 Phase 7A: OCR smart fallback (not enabled by default)
        # do_ocr=False means native parser first, then OCR fallback if text density < 80 chars/page
        assert config.do_ocr is False, "OCR should be disabled by default (smart fallback via _should_retry_with_ocr)"
        assert config.ocr_retry_min_chars_per_page == 80

        # Task 1: Image/table extraction enabled by default (was False)
        assert config.generate_picture_images is True, (
            "Picture extraction should be enabled"
        )
        assert config.generate_table_images is True, (
            "Table extraction should be enabled"
        )

        # Safety limits
        assert config.max_num_pages == 100
        assert config.max_file_size_mb == 50
        assert config.timeout_seconds == 300

    def test_parser_config_custom_values(self):
        """Test ParserConfig accepts custom values."""
        config = ParserConfig(
            do_ocr=False,
            generate_picture_images=False,
            generate_table_images=False,
            max_num_pages=50,
            max_file_size_mb=30,
            timeout_seconds=180,
        )

        assert config.do_ocr is False
        assert config.generate_picture_images is False
        assert config.generate_table_images is False
        assert config.max_num_pages == 50
        assert config.max_file_size_mb == 30
        assert config.timeout_seconds == 180

    def test_parser_config_from_settings(self):
        """Test ParserConfig loads from application settings."""
        config = ParserConfig.from_settings()

        # Should match settings defaults (per PR7: smart fallback)
        assert config.do_ocr is False  # Native parser first, OCR fallback only if needed
        assert config.ocr_retry_min_chars_per_page == 80
        assert config.max_file_size_mb == 50
        assert config.timeout_seconds == 300


class TestDoclingParserConfig:
    """Tests for DoclingParser configuration integration."""

    def test_docling_parser_uses_config(self):
        """Test DoclingParser uses ParserConfig for initialization."""
        config = ParserConfig(
            do_ocr=True,
            generate_picture_images=True,
            generate_table_images=True,
        )
        parser = DoclingParser(config=config)

        # Verify config is stored
        assert parser.config is not None
        assert parser.config.do_ocr is True
        assert parser.config.generate_picture_images is True
        assert parser.config.generate_table_images is True

    def test_docling_parser_defaults_from_settings(self):
        """Test DoclingParser defaults load from settings when config not provided."""
        parser = DoclingParser()

        # Should use defaults from settings (per PR7: smart fallback)
        assert parser.config.do_ocr is False  # Native first, OCR fallback only if text density low
        assert parser.config.generate_picture_images is True
        assert parser.config.generate_table_images is True

    def test_docling_parser_pipeline_options_match_config(self):
        """Test DoclingParser creates pipeline options from config."""
        config = ParserConfig(
            do_ocr=True,
            generate_picture_images=True,
            generate_table_images=True,
        )
        parser = DoclingParser(config=config)

        # Pipeline options should match config
        assert parser.pipeline_options.do_ocr is True
        assert parser.pipeline_options.generate_picture_images is True
        assert parser.pipeline_options.generate_table_images is True

    def test_docling_parser_prewarm_initializes_native_converter(self):
        """Prewarm should initialize the native converter without a real parse."""
        parser = DoclingParser(config=ParserConfig(do_ocr=False))
        assert parser._native_converter is None

        parser.prewarm()

        assert parser._native_converter is not None
        assert parser._ocr_converter is None

    def test_get_docling_parser_returns_singleton(self):
        """Worker runtime should reuse a shared parser instance."""
        parser_a = get_docling_parser()
        parser_b = get_docling_parser()

        assert parser_a is parser_b


class TestDoclingParserForceOCR:
    """Tests for force_ocr override parameter (Task 1)."""

    @pytest.mark.asyncio
    async def test_force_ocr_override_creates_new_converter(self):
        """Test force_ocr=True uses OCR converter even when default do_ocr is False."""
        config = ParserConfig(do_ocr=False)
        parser = DoclingParser(config=config)

        # Create mock PDF path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test content")
            tmp_path = tmp.name

        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "OCR extracted text content"
        mock_doc.iterate_items.return_value = []
        mock_doc.pages = [Mock()]
        mock_doc.name = "ocr.pdf"

        mock_result = Mock(document=mock_doc)

        with patch.object(parser.native_converter, "convert", side_effect=AssertionError("Native converter should not run when force_ocr=True")), patch.object(
            parser.ocr_converter,
            "convert",
            return_value=mock_result,
        ) as ocr_convert:
            result = await parser.parse_pdf(tmp_path, force_ocr=True)

        assert result["metadata"]["parse_mode"] == "force_ocr"
        assert result["metadata"]["ocr_used"] is True
        assert "force_ocr_override" in result["metadata"]["parse_warnings"]
        ocr_convert.assert_called_once()

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


class TestDoclingParserFileSizeLimit:
    """Tests for file size limit enforcement (Task 3)."""

    @pytest.mark.asyncio
    async def test_file_too_large_error_raised(self):
        """Test FileTooLargeError is raised for oversized files."""
        parser = DoclingParser(config=ParserConfig(max_file_size_mb=1))

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4")
            tmp.write(b"\x00" * (2 * 1024 * 1024))
            tmp_path = tmp.name

        with pytest.raises(FileTooLargeError, match="exceeds limit"):
            await parser.parse_pdf(tmp_path)

        Path(tmp_path).unlink(missing_ok=True)


class TestDoclingParserPageLimit:
    """Tests for page limit enforcement."""

    @pytest.mark.asyncio
    async def test_parse_pdf_checks_page_limit_before_processing_items(self):
        config = ParserConfig(max_num_pages=1)
        parser = DoclingParser(config=config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test")
            tmp_path = tmp.name

        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "test markdown"
        mock_doc.iterate_items.return_value = []
        mock_doc.pages = [Mock(), Mock()]  # 2 pages > limit 1
        mock_doc.name = "too-many-pages.pdf"

        mock_result = Mock(document=mock_doc)

        with patch.object(parser.native_converter, "convert", return_value=mock_result):
            with pytest.raises(PageLimitError, match="exceeds page limit"):
                await parser.parse_pdf(tmp_path)

        Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_parse_pdf_checks_file_size_before_parsing(self):
        """Test parse_pdf checks file size before parsing."""
        config = ParserConfig(max_file_size_mb=1)
        parser = DoclingParser(config=config)

        # Create oversized test file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4")
            tmp.write(b"\x00" * (2 * 1024 * 1024))  # 2MB
            tmp_path = tmp.name

        # Should raise FileTooLargeError
        with pytest.raises(FileTooLargeError, match="exceeds limit"):
            await parser.parse_pdf(tmp_path)

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


class TestDoclingParserTimeout:
    """Tests for timeout protection (Task 3)."""

    @pytest.mark.asyncio
    async def test_timeout_raises_parse_timeout_error(self):
        """Test ParseTimeoutError is raised when parsing exceeds timeout."""
        config = ParserConfig(timeout_seconds=2)  # 2s timeout for testing
        parser = DoclingParser(config=config)

        # Create valid test file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test")
            tmp_path = tmp.name

        # Mock converter.convert to take longer than timeout
        def slow_convert(*args, **kwargs):
            import time

            time.sleep(3)  # Sleep 3s, exceeds 2s timeout
            return Mock(
                document=Mock(
                    export_to_markdown=lambda: "", iterate_items=lambda: [], pages=[]
                )
            )

        with patch.object(parser.native_converter, "convert", side_effect=slow_convert):
            # Should raise ParseTimeoutError
            with pytest.raises(ParseTimeoutError, match="exceeded timeout"):
                await parser.parse_pdf(tmp_path)

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


class TestFieldContractUnification:
    """Tests for Task 2: Field contract unification (page_count vs pages)."""

    @pytest.mark.asyncio
    async def test_parse_result_has_page_count_field(self):
        """Test parse_result uses 'page_count' field (not 'pages')."""
        parser = DoclingParser()

        # Create test file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test")
            tmp_path = tmp.name

        # Mock converter to return document with pages
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "test markdown"
        mock_doc.iterate_items.return_value = []
        mock_doc.pages = [Mock(), Mock()]  # 2 pages
        mock_doc.name = "test.pdf"

        mock_result = Mock()
        mock_result.document = mock_doc

        with patch.object(parser.native_converter, "convert", return_value=mock_result), patch.object(
            parser.ocr_converter, "convert", return_value=mock_result
        ):
            result = await parser.parse_pdf(tmp_path)

            # Task 2: Should have 'page_count' field (not 'pages' array)
            assert "page_count" in result, "parse_result should have 'page_count' field"
            assert result["page_count"] == 2, "page_count should equal number of pages"

            # Should NOT have 'pages' array field
            assert "pages" not in result, "parse_result should NOT have 'pages' field"

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


class TestDoclingParserReturnStructure:
    """Tests for parse_pdf return structure."""

    @pytest.mark.asyncio
    async def test_parse_pdf_returns_required_fields(self):
        """Test parse_pdf returns all required fields."""
        parser = DoclingParser()

        # Create test file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test")
            tmp_path = tmp.name

        # Mock converter
        mock_doc = Mock()
        mock_doc.export_to_markdown.return_value = "test"
        mock_doc.iterate_items.return_value = []
        mock_doc.pages = []
        mock_doc.name = "test.pdf"

        mock_result = Mock()
        mock_result.document = mock_doc

        with patch.object(parser.native_converter, "convert", return_value=mock_result):
            result = await parser.parse_pdf(tmp_path)

            # Verify all required fields
            assert "markdown" in result
            assert "items" in result
            assert "page_count" in result
            assert "metadata" in result

            assert isinstance(result["markdown"], str)
            assert isinstance(result["items"], list)
            assert isinstance(result["page_count"], int)
            assert isinstance(result["metadata"], dict)

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
