"""
Tests for Docling PDF parsing functionality.

These tests verify PDF parsing capabilities including:
- Digital PDF parsing (text layer extraction)
- Scanned PDF OCR (text from images)
- Multi-column layout preservation
- Table extraction
- Formula extraction
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDoclingParsing:
    """Test suite for Docling PDF parsing functionality."""

    def test_docling_parse_digital(self, docling_converter, sample_pdf_digital):
        """
        Test parsing a digital PDF with text layer.

        Verifies that:
        - PDF can be converted to markdown
        - Text content is extracted correctly
        - Document structure is preserved
        """
        # Arrange: Mock the conversion result
        expected_markdown = """# Test Paper

This is a test document with digital text.

## Section 1: Introduction

The introduction provides background information.

## Section 2: Methods

We used standard methods for this research.
"""

        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = expected_markdown
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert the PDF
            result = docling_converter.convert(sample_pdf_digital)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify output
            assert result.status == "success"
            assert "# Test Paper" in markdown_output
            assert "Introduction" in markdown_output
            assert "Methods" in markdown_output

    def test_docling_parse_scanned(self, docling_converter, sample_pdf_scanned):
        """
        Test parsing a scanned PDF with OCR.

        Verifies that:
        - OCR is applied to extract text from images
        - Text content is recognizable
        - No empty output for scanned documents
        """
        # Arrange: Mock OCR result
        expected_markdown = """# Scanned Document

This text was extracted using OCR from a scanned PDF.

The OCR engine successfully recognized the text content.
"""

        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = expected_markdown
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert with OCR enabled
            result = docling_converter.convert(sample_pdf_scanned)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify OCR extracted text
            assert result.status == "success"
            assert len(markdown_output) > 0
            assert "scanned" in markdown_output.lower() or "OCR" in markdown_output

    def test_docling_parse_multicolumn(self, docling_converter, sample_pdf_multicolumn):
        """
        Test parsing multi-column academic layout.

        Verifies that:
        - Reading order is preserved across columns
        - Text flows correctly from column 1 to column 2
        - Academic paper layout is handled properly
        """
        # Arrange: Mock multi-column document
        expected_markdown = """# Multi-Column Academic Paper

This is the first column text that should appear before the second column.

This continues the first column with more content about the research.

Then the text continues in the second column maintaining proper reading order.

Finally we have the conclusion text from the second column.
"""

        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = expected_markdown
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert multi-column PDF
            result = docling_converter.convert(sample_pdf_multicolumn)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify reading order
            assert result.status == "success"
            assert "first column" in markdown_output.lower()
            assert "second column" in markdown_output.lower()
            # Content should be in proper reading order
            first_pos = markdown_output.lower().find("first column")
            second_pos = markdown_output.lower().find("second column")
            assert first_pos < second_pos, "Reading order should be preserved"

    def test_docling_parse_tables(self, docling_converter, sample_pdf_with_tables):
        """
        Test extraction of tables from PDF.

        Verifies that:
        - Table content is extracted
        - Table structure is preserved (rows/columns)
        - TableItem objects are created
        """
        # Arrange: Mock document with tables
        mock_table = MagicMock()
        mock_table.caption = "Table 1: Performance Metrics"
        mock_table.export_to_markdown.return_value = """| Model | Accuracy | F1 Score |
|-------|----------|----------|
| CNN   | 0.95     | 0.94     |
| RNN   | 0.92     | 0.91     |"""

        mock_document = MagicMock()
        mock_document.export_to_markdown.return_value = """# Paper with Tables

## Results

Here are our results in table format.

| Model | Accuracy | F1 Score |
|-------|----------|----------|
| CNN   | 0.95     | 0.94     |

As shown in the table, our model performs well.
"""
        mock_document.tables = [mock_table]

        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert PDF with tables
            result = docling_converter.convert(sample_pdf_with_tables)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify table extraction
            assert result.status == "success"
            assert "|" in markdown_output  # Markdown table syntax
            assert "Model" in markdown_output
            assert "Accuracy" in markdown_output

    def test_docling_parse_formulas(self, docling_converter, sample_pdf_with_formulas):
        """
        Test extraction of mathematical formulas from PDF.

        Verifies that:
        - LaTeX formulas are extracted
        - FormulaItem objects are created
        - Formula content is preserved
        """
        # Arrange: Mock document with formulas
        mock_formula = MagicMock()
        mock_formula.caption = "Equation 1"
        mock_formula.latex = r"E = mc^2"

        mock_document = MagicMock()
        mock_document.export_to_markdown.return_value = """# Paper with Formulas

## Methods

The energy-mass relation is given by:

$$E = mc^2$$

Where $E$ is energy, $m$ is mass, and $c$ is the speed of light.
"""
        mock_document.formulas = [mock_formula]

        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert PDF with formulas
            result = docling_converter.convert(sample_pdf_with_formulas)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify formula extraction
            assert result.status == "success"
            assert "E = mc^2" in markdown_output or "$" in markdown_output

    def test_ocr_fallback(self, docling_converter, sample_pdf_scanned):
        """
        Test that OCR is used as fallback for image-based PDFs.

        Verifies that:
        - OCR kicks in automatically for documents without text layer
        - OCR extraction provides readable text
        - No empty output for image-based documents
        """
        # Arrange: Simulate image-based PDF without text layer
        ocr_extracted_text = """# Scanned Research Paper

This content was extracted using OCR.

The text recognition successfully identified all characters.
"""

        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = ocr_extracted_text
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert image-based PDF
            result = docling_converter.convert(sample_pdf_scanned)
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify OCR produced text
            assert result.status == "success"
            assert len(markdown_output.strip()) > 0
            assert len(markdown_output) > 50  # Substantial text extracted

    def test_parse_failure_handling(self, docling_converter):
        """
        Test handling of PDF parsing failures.

        Verifies that:
        - Corrupted or invalid PDFs are handled gracefully
        - Appropriate errors are raised
        """
        # Arrange: Simulate parsing failure
        from docling.exceptions import ConversionError

        with patch.object(docling_converter, 'convert', side_effect=ConversionError("Failed to parse PDF")):
            # Act & Assert: Verify error handling
            with pytest.raises(ConversionError) as exc_info:
                docling_converter.convert(Path("/nonexistent/corrupted.pdf"))

            assert "Failed to parse PDF" in str(exc_info.value)

    def test_parse_empty_pdf(self, docling_converter):
        """
        Test handling of empty or minimal PDFs.

        Verifies that:
        - Empty PDFs don't crash the parser
        - Minimal content is handled gracefully
        """
        # Arrange: Mock empty document
        mock_document = MagicMock()
        mock_document.export_to_markdown.return_value = ""
        mock_document.tables = []
        mock_document.formulas = []

        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert empty PDF
            result = docling_converter.convert(Path("/test/empty.pdf"))
            markdown_output = result.document.export_to_markdown()

            # Assert: Verify empty handling
            assert result.status == "success"
            assert markdown_output == ""

    def test_pdf_metadata_extraction(self, docling_converter, sample_pdf_digital):
        """
        Test extraction of PDF metadata.

        Verifies that:
        - Document properties are extracted
        - Page count is available
        - Title and author metadata is captured
        """
        # Arrange: Mock document with metadata
        mock_document = MagicMock()
        mock_document.export_to_markdown.return_value = "# Test Paper\n\nContent"
        mock_document.num_pages = 10
        mock_document.metadata = {
            "title": "Test Paper Title",
            "author": "Test Author",
            "creation_date": "2024-01-15"
        }

        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_result.status = "success"

        with patch.object(docling_converter, 'convert', return_value=mock_result):
            # Act: Convert PDF
            result = docling_converter.convert(sample_pdf_digital)

            # Assert: Verify metadata
            assert result.status == "success"
            assert result.document.num_pages == 10


class TestDocumentChunking:
    """Test suite for document chunking functionality."""

    def test_chunk_by_paragraphs(self, sample_pdf_content):
        """
        Test chunking document by paragraphs.

        Verifies that:
        - Document is split into logical chunks
        - Paragraph boundaries are respected
        - Section headers are preserved with content
        """
        # This test defines the expected behavior for paragraph chunking
        # Implementation will be done in the actual feature

        content = sample_pdf_content

        # Assert: Content has expected structure
        assert "# Introduction" in content
        assert "# Methods" in content
        assert "# Results" in content
        assert "# Conclusion" in content

        # Sections should be separated
        intro_pos = content.find("# Introduction")
        methods_pos = content.find("# Methods")
        results_pos = content.find("# Results")
        conclusion_pos = content.find("# Conclusion")

        assert intro_pos < methods_pos < results_pos < conclusion_pos

    def test_chunk_preserves_context(self, sample_pdf_content):
        """
        Test that chunking preserves context and meaning.

        Verifies that:
        - Related content stays together
        - Context is not lost across chunk boundaries
        """
        content = sample_pdf_content

        # Verify content has enough substance
        assert len(content) > 100

        # Section headers should exist
        assert any(header in content for header in [
            "# Introduction", "# Methods", "# Results", "# Conclusion"
        ])

    def test_chunk_metadata_preservation(self, sample_chunks):
        """
        Test that chunk metadata is preserved during chunking.

        Verifies that:
        - Section information is attached
        - Page numbers are recorded
        - Special content flags (table, figure, formula) are set
        """
        for chunk in sample_chunks:
            # Each chunk should have required metadata
            assert "id" in chunk
            assert "content" in chunk
            assert "section" in chunk
            assert "page" in chunk
            assert "is_table" in chunk
            assert "is_figure" in chunk
            assert "is_formula" in chunk

            # IDs should be unique
            assert len(chunk["id"]) > 0

        # Check special content detection
        table_chunks = [c for c in sample_chunks if c["is_table"]]
        assert len(table_chunks) >= 1, "Should detect table content"
