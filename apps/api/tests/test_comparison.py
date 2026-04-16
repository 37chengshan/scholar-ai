"""Tests for the comparison API.

Tests multi-paper comparison functionality including:
- Paper fetching and validation
- LLM-powered comparison analysis
- Markdown table generation
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.api.compare import (
    CompareRequest,
    CompareResponse,
    ComparisonResult,
    fetch_papers_for_comparison,
    generate_markdown_table,
    analyze_papers_with_llm,
)


class TestCompareRequest:
    """Test CompareRequest model validation."""

    def test_valid_request_with_two_papers(self):
        """Test valid request with minimum 2 papers."""
        request = CompareRequest(
            paper_ids=["paper-1", "paper-2"],
            dimensions=["method", "results"]
        )
        assert len(request.paper_ids) == 2
        assert request.dimensions == ["method", "results"]

    def test_valid_request_with_ten_papers(self):
        """Test valid request with maximum 10 papers."""
        request = CompareRequest(
            paper_ids=[f"paper-{i}" for i in range(10)],
            dimensions=["method", "results", "dataset"]
        )
        assert len(request.paper_ids) == 10

    def test_invalid_request_with_one_paper(self):
        """Test that 1 paper raises validation error."""
        with pytest.raises(ValueError):
            CompareRequest(
                paper_ids=["paper-1"],
                dimensions=["method"]
            )

    def test_invalid_request_with_eleven_papers(self):
        """Test that 11 papers raises validation error."""
        with pytest.raises(ValueError):
            CompareRequest(
                paper_ids=[f"paper-{i}" for i in range(11)],
                dimensions=["method"]
            )

    def test_default_dimensions(self):
        """Test default dimensions are applied."""
        request = CompareRequest(
            paper_ids=["paper-1", "paper-2"],
        )
        assert request.dimensions == ["method", "results", "dataset", "metrics"]

    def test_default_include_abstract(self):
        """Test default include_abstract is True."""
        request = CompareRequest(
            paper_ids=["paper-1", "paper-2"],
        )
        assert request.include_abstract is True


class TestFetchPapersForComparison:
    """Test fetch_papers_for_comparison function."""

    @pytest.mark.asyncio
    async def test_fetch_papers_returns_papers_with_chunks(self):
        """Test successful fetch returns papers with metadata and chunks."""
        mock_papers = [
            {
                "id": "paper-1",
                "title": "Test Paper 1",
                "authors": ["Author A"],
                "year": 2024,
                "abstract": "Abstract 1",
                "status": "completed"
            },
            {
                "id": "paper-2",
                "title": "Test Paper 2",
                "authors": ["Author B"],
                "year": 2023,
                "abstract": "Abstract 2",
                "status": "completed"
            }
        ]

        mock_chunks_p1 = [
            {"content": "Chunk 1 content", "section": "Introduction", "page": 1},
            {"content": "Chunk 2 content", "section": "Methods", "page": 2},
        ]

        mock_chunks_p2 = [
            {"content": "Chunk 3 content", "section": "Results", "page": 3},
        ]

        # Mock the database connection with sequential calls
        mock_conn = AsyncMock()
        # First call returns papers, subsequent calls return chunks for each paper
        mock_conn.fetch = AsyncMock(side_effect=[mock_papers, mock_chunks_p1, mock_chunks_p2])

        with patch('app.api.compare.get_db_connection') as mock_get_conn:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await fetch_papers_for_comparison(
                paper_ids=["paper-1", "paper-2"],
                user_id="user-1"
            )

            assert len(result) == 2
            assert result[0]["id"] == "paper-1"
            assert result[1]["id"] == "paper-2"
            assert "chunks" in result[0]
            assert len(result[0]["chunks"]) == 2
            assert len(result[1]["chunks"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_papers_missing_papers_raises_404(self):
        """Test that missing paper IDs raise 404 error."""
        mock_papers = [
            {
                "id": "paper-1",
                "title": "Test Paper 1",
                "authors": ["Author A"],
                "year": 2024,
                "abstract": "Abstract 1",
                "status": "completed"
            }
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_papers)

        with patch('app.api.compare.get_db_connection') as mock_get_conn:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            with pytest.raises(HTTPException) as exc_info:
                await fetch_papers_for_comparison(
                    paper_ids=["paper-1", "paper-2"],
                    user_id="user-1"
                )

            assert exc_info.value.status_code == 404
            assert "paper-2" in str(exc_info.value.detail)


class TestGenerateMarkdownTable:
    """Test Markdown table generation."""

    def test_markdown_table_generation(self):
        """Test Markdown table is generated correctly."""
        comparison_data = {
            "comparison_table": {
                "headers": ["Paper", "Method", "Results"],
                "rows": [
                    ["Paper A", "CNN", "95% accuracy"],
                    ["Paper B", "Transformer", "97% accuracy"]
                ]
            }
        }

        markdown = generate_markdown_table(comparison_data)

        assert "| Paper | Method | Results |" in markdown
        assert "| --- | --- | --- |" in markdown
        assert "| Paper A | CNN | 95% accuracy |" in markdown
        assert "| Paper B | Transformer | 97% accuracy |" in markdown

    def test_markdown_table_truncates_long_cells(self):
        """Test long cell values are truncated."""
        comparison_data = {
            "comparison_table": {
                "headers": ["Paper", "Description"],
                "rows": [
                    ["Paper A", "A" * 150]  # 150 characters, should be truncated
                ]
            }
        }

        markdown = generate_markdown_table(comparison_data)

        assert "..." in markdown
        assert "A" * 100 in markdown
        assert "A" * 101 not in markdown

    def test_markdown_table_empty_data(self):
        """Test empty data handling."""
        comparison_data = {
            "comparison_table": {
                "headers": [],
                "rows": []
            }
        }

        markdown = generate_markdown_table(comparison_data)
        assert "No comparison data available" in markdown


class TestAnalyzePapersWithLLM:
    """Test LLM-powered comparison analysis."""

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_llm_analysis_returns_structured_data(self, mock_litellm):
        """Test LLM analysis returns structured comparison data."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"comparison_table": {"headers": ["Paper", "Method"], "rows": [["P1", "CNN"]]}, "findings": [{"paper_id": "p1", "title": "Test", "findings": {"method": "CNN"}}], "summary": "Test summary"}'
                    }
                }
            ]
        }
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        papers = [
            {
                "id": "p1",
                "title": "Test Paper",
                "authors": ["Author"],
                "year": 2024,
                "abstract": "Abstract",
                "chunks": [
                    {"content": "Content 1", "section": "Methods", "page": 1}
                ]
            }
        ]

        result = await analyze_papers_with_llm(papers, ["method"])

        assert "comparison_table" in result
        assert "findings" in result
        assert "summary" in result
        mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_llm_analysis_handles_errors(self, mock_litellm):
        """Test LLM analysis handles errors gracefully."""
        mock_litellm.acompletion = AsyncMock(side_effect=Exception("LLM error"))

        papers = [
            {
                "id": "p1",
                "title": "Test Paper",
                "authors": ["Author"],
                "year": 2024,
                "abstract": "Abstract",
                "chunks": []
            }
        ]

        with pytest.raises(HTTPException) as exc_info:
            await analyze_papers_with_llm(papers, ["method"])

        assert exc_info.value.status_code == 500
        assert "Failed to generate comparison" in exc_info.value.detail


class TestCompareResponse:
    """Test CompareResponse model."""

    def test_response_structure(self):
        """Test response has all required fields."""
        response = CompareResponse(
            paper_ids=["paper-1", "paper-2"],
            dimensions=["method", "results"],
            markdown_table="| Paper | Method |\n| --- | --- |\n| P1 | CNN |",
            structured_data=[
                ComparisonResult(
                    paper_id="paper-1",
                    title="Test Paper",
                    authors=["Author"],
                    year=2024,
                    findings={"method": "CNN"}
                )
            ],
            summary="Test summary"
        )

        assert response.paper_ids == ["paper-1", "paper-2"]
        assert response.markdown_table is not None
        assert len(response.structured_data) == 1
        assert response.summary == "Test summary"
