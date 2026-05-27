"""Tests for TableExtractor service.

Tests cover:
- Table extraction from Docling items
- Table structure parsing (headers, rows)
- Description generation integration
- Embedding generation via BGE-M3
- Error handling and edge cases
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.core.table_extractor import TableExtractor, TableData


class TestTableExtractor:
    """Test TableExtractor functionality."""

    def test_init(self):
        """Test TableExtractor initialization."""
        extractor = TableExtractor()
        assert extractor is not None

    def test_extract_tables_from_pdf_success(self):
        """Test successful table extraction from Docling items."""
        extractor = TableExtractor()

        # Docling items with table
        docling_items = [
            {"type": "table", "page": 1, "text": "| Name | Value |\n|------|-------|\n| A | 10 |\n| B | 20 |"},
            {"type": "text", "page": 1, "text": "Some text"},
        ]

        tables = extractor.extract_tables_from_pdf(docling_items)

        assert len(tables) == 1
        assert tables[0].page_num == 1
        assert tables[0].markdown == "| Name | Value |\n|------|-------|\n| A | 10 |\n| B | 20 |"

    def test_extract_tables_no_tables(self):
        """Test extraction when no tables in items."""
        extractor = TableExtractor()

        docling_items = [
            {"type": "text", "page": 1, "text": "Some text"},
            {"type": "picture", "page": 1},
        ]

        tables = extractor.extract_tables_from_pdf(docling_items)

        assert len(tables) == 0

    def test_extract_tables_missing_text(self):
        """Test extraction with table missing text field."""
        extractor = TableExtractor()

        docling_items = [
            {"type": "table", "page": 1},  # No text field
        ]

        tables = extractor.extract_tables_from_pdf(docling_items)

        # Should skip tables without text
        assert len(tables) == 0

    def test_parse_table_markdown_simple(self):
        """Test parsing simple markdown table."""
        extractor = TableExtractor()

        markdown = "| Name | Value |\n|------|-------|\n| A | 10 |\n| B | 20 |"

        headers, rows = extractor._parse_table_markdown(markdown)

        assert headers == ["Name", "Value"]
        assert len(rows) == 2
        assert rows[0] == {"Name": "A", "Value": "10"}
        assert rows[1] == {"Name": "B", "Value": "20"}

    def test_parse_table_markdown_with_caption(self):
        """Test parsing table with caption."""
        extractor = TableExtractor()

        markdown = "Table 1: Sample Data\n\n| Name | Value |\n|------|-------|\n| A | 10 |"

        headers, rows = extractor._parse_table_markdown(markdown)

        assert headers == ["Name", "Value"]
        assert len(rows) == 1

    def test_parse_table_markdown_malformed(self):
        """Test parsing malformed markdown table."""
        extractor = TableExtractor()

        markdown = "This is not a table"

        headers, rows = extractor._parse_table_markdown(markdown)

        assert headers == []
        assert rows == []

    def test_parse_table_markdown_empty(self):
        """Test parsing empty markdown."""
        extractor = TableExtractor()

        headers, rows = extractor._parse_table_markdown("")

        assert headers == []
        assert rows == []

    def test_extract_caption(self):
        """Test caption extraction from markdown."""
        extractor = TableExtractor()

        markdown = "Table 1: Performance Metrics\n\n| Name | Value |"

        caption = extractor._extract_caption(markdown)

        assert caption == "Table 1: Performance Metrics"

    def test_extract_caption_no_caption(self):
        """Test caption extraction when no caption present."""
        extractor = TableExtractor()

        markdown = "| Name | Value |\n|------|-------|"

        caption = extractor._extract_caption(markdown)

        assert caption == ""

    @patch('app.core.table_extractor.get_multimodal_embedding_service')
    async def test_generate_description_and_embed_success(self, mock_multimodal):
        """Test successful direct table embedding generation."""
        mock_qwen_service = Mock()
        mock_qwen_service.encode_table.return_value = [0.2] * 2048
        mock_multimodal.return_value = mock_qwen_service

        # Create extractor
        extractor = TableExtractor()

        # Create TableData
        table_data = TableData(
            page_num=1,
            markdown="| Name | Value |\n| A | 10 |",
            headers=["Name", "Value"],
            rows=[{"Name": "A", "Value": "10"}]
        )

        # Generate description and embed
        result = await extractor.generate_description_and_embed(
            table_data,
            paper_id="paper-123",
            user_id="user-456"
        )

        # Verify
        assert result["paper_id"] == "paper-123"
        assert result["user_id"] == "user-456"
        assert result["page_num"] == 1
        assert result["content_type"] == "table"
        assert result["content_data"] == "Table: \nColumns: Name, Value\nSample data: [{'Name': 'A', 'Value': '10'}]"
        assert result["embedding"] == [0.2] * 2048
        assert result["raw_data"]["headers"] == ["Name", "Value"]
        assert result["raw_data"]["row_count"] == 1

        mock_qwen_service.encode_table.assert_called_once_with(
            caption="",
            headers=["Name", "Value"],
            rows=[{"Name": "A", "Value": "10"}],
        )

    @patch('app.core.table_extractor.get_multimodal_embedding_service')
    async def test_generate_description_and_embed_no_description(self, mock_multimodal):
        """Test table serialization when markdown has no caption."""
        mock_qwen_service = Mock()
        mock_qwen_service.encode_table.return_value = [0.0] * 2048
        mock_multimodal.return_value = mock_qwen_service

        extractor = TableExtractor()
        table_data = TableData(
            page_num=1,
            markdown="| Name | Value |",
            headers=["Name", "Value"],
            rows=[{"Name": "A", "Value": "10"}]
        )

        result = await extractor.generate_description_and_embed(
            table_data,
            paper_id="paper-123",
            user_id="user-456"
        )

        assert result["content_data"] == "Table: \nColumns: Name, Value\nSample data: [{'Name': 'A', 'Value': '10'}]"
        assert result["embedding"] == [0.0] * 2048

    @patch('app.core.table_extractor.get_multimodal_embedding_service')
    async def test_generate_description_and_embed_service_error(self, mock_multimodal):
        """Test fallback behavior when table encoding fails."""
        mock_qwen_service = Mock()
        mock_qwen_service.encode_table.side_effect = Exception("Encoding error")
        mock_multimodal.return_value = mock_qwen_service

        extractor = TableExtractor()
        table_data = TableData(
            page_num=1,
            markdown="| Name | Value |",
            headers=["Name", "Value"],
            rows=[{"Name": "A", "Value": "10"}]
        )

        result = await extractor.generate_description_and_embed(
            table_data,
            paper_id="paper-123",
            user_id="user-456"
        )

        assert result["content_data"] == "Table: \nColumns: Name, Value\nSample data: [{'Name': 'A', 'Value': '10'}]"
        assert result["embedding"] == [0.0] * 2048


class TestTableData:
    """Test TableData dataclass."""

    def test_table_data_creation(self):
        """Test TableData creation."""
        data = TableData(
            page_num=2,
            markdown="| A | B |",
            headers=["A", "B"],
            rows=[{"A": "1", "B": "2"}]
        )

        assert data.page_num == 2
        assert data.markdown == "| A | B |"
        assert data.headers == ["A", "B"]
        assert data.rows == [{"A": "1", "B": "2"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
