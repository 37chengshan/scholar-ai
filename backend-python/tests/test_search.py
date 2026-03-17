"""Tests for external search API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestArxivSearch:
    """Tests for arXiv search endpoint."""

    def test_search_arxiv_no_query(self):
        """Test that search requires query parameter."""
        response = client.get("/search/arxiv")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_arxiv_with_query(self, monkeypatch):
        """Test searching arXiv with a query."""
        # Mock the httpx request
        import httpx

        class MockResponse:
            text = """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <entry>
                    <id>http://arxiv.org/abs/1234.5678</id>
                    <title>Test Paper</title>
                    <summary>Test abstract</summary>
                    <published>2024-01-15T00:00:00Z</published>
                    <author><name>John Doe</name></author>
                    <link href="http://arxiv.org/pdf/1234.5678.pdf" title="pdf"/>
                </entry>
            </feed>"""
            status_code = 200

            def raise_for_status(self):
                pass

        async def mock_get(*args, **kwargs):
            return MockResponse()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        response = client.get("/search/arxiv?query=machine+learning&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestSemanticScholarSearch:
    """Tests for Semantic Scholar search endpoint."""

    def test_search_semantic_scholar_no_query(self):
        """Test that search requires query parameter."""
        response = client.get("/search/semantic-scholar")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_semantic_scholar_with_query(self, monkeypatch):
        """Test searching Semantic Scholar with a query."""
        import httpx

        class MockResponse:
            def json(self):
                return {
                    "data": [
                        {
                            "paperId": "abc123",
                            "title": "Test Paper",
                            "year": 2024,
                            "abstract": "Test abstract",
                            "authors": [{"name": "John Doe"}],
                            "openAccessPdf": {"url": "https://example.com/pdf.pdf"},
                        }
                    ]
                }

            status_code = 200

            def raise_for_status(self):
                pass

        async def mock_get(*args, **kwargs):
            return MockResponse()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        response = client.get("/search/semantic-scholar?query=machine+learning&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestSearchResultFormat:
    """Tests for search result format."""

    def test_result_has_required_fields(self):
        """Test that results have all required fields."""
        from app.api.search import SearchResult

        result = SearchResult(
            id="test123",
            title="Test Paper",
            authors=["John Doe"],
            year=2024,
            abstract="Test abstract",
            source="arxiv",
            pdfUrl="https://example.com/pdf.pdf",
            url="https://example.com/abs/test123",
        )

        assert result.id == "test123"
        assert result.title == "Test Paper"
        assert result.authors == ["John Doe"]
        assert result.year == 2024
        assert result.abstract == "Test abstract"
        assert result.source == "arxiv"
        assert result.pdfUrl == "https://example.com/pdf.pdf"
        assert result.url == "https://example.com/abs/test123"
