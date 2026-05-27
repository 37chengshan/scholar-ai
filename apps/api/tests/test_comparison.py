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
        paper_rows = [
            MagicMock(
                id="paper-1",
                title="Test Paper 1",
                authors=["Author A"],
                year=2024,
                abstract="Abstract 1",
                status="completed",
            ),
            MagicMock(
                id="paper-2",
                title="Test Paper 2",
                authors=["Author B"],
                year=2023,
                abstract="Abstract 2",
                status="completed",
            ),
        ]
        chunk_rows_p1 = [
            MagicMock(content="Chunk 1 content", section="Introduction", page_start=1, id="c1"),
            MagicMock(content="Chunk 2 content", section="Methods", page_start=2, id="c2"),
        ]
        chunk_rows_p2 = [
            MagicMock(content="Chunk 3 content", section="Results", page_start=3, id="c3"),
        ]
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=paper_rows)))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=chunk_rows_p1)))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=chunk_rows_p2)))),
            ]
        )

        result = await fetch_papers_for_comparison(
            paper_ids=["paper-1", "paper-2"],
            user_id="user-1",
            db=mock_conn,
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
        paper_rows = [
            MagicMock(
                id="paper-1",
                title="Test Paper 1",
                authors=["Author A"],
                year=2024,
                abstract="Abstract 1",
                status="completed",
            )
        ]
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=paper_rows)))
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await fetch_papers_for_comparison(
                paper_ids=["paper-1", "paper-2"],
                user_id="user-1",
                db=mock_conn,
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
    @patch('app.api.compare.get_llm_client')
    async def test_llm_analysis_returns_structured_data(self, mock_get_llm_client):
        """Test LLM analysis returns structured comparison data."""
        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"comparison_table": {"headers": ["Paper", "Method"], "rows": [["P1", "CNN"]]}, "findings": [{"paper_id": "p1", "title": "Test", "findings": {"method": "CNN"}}], "summary": "Test summary"}'
                        )
                    )
                ]
            )
        )
        mock_get_llm_client.return_value = mock_client

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
        mock_client.chat_completion.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('app.api.compare.get_llm_client')
    async def test_llm_analysis_handles_errors(self, mock_get_llm_client):
        """Test LLM analysis handles errors gracefully."""
        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_llm_client.return_value = mock_client

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
        assert "Failed to generate comparison" in exc_info.value.detail["detail"]


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
