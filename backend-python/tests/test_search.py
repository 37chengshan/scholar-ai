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


class TestFusionSearch:
    """Tests for fusion search endpoint."""

    @pytest.mark.asyncio
    async def test_fusion_search_returns_merged_results(self, monkeypatch):
        """Test that fusion search returns merged results from library + arXiv + S2."""
        import httpx
        from app.core.multimodal_search_service import get_multimodal_search_service

        # Mock Milvus search (library)
        class MockMultimodalService:
            async def search(self, **kwargs):
                return {
                    "results": [
                        {
                            "id": "lib-1",
                            "title": "Library Paper",
                            "content_data": "Abstract from library",
                            "year": 2024,
                            "source": "library",
                        }
                    ]
                }

        monkeypatch.setattr(
            "app.api.search.get_multimodal_search_service",
            lambda: MockMultimodalService()
        )

        # Mock arXiv response
        class MockArxivResponse:
            text = """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <entry>
                    <id>http://arxiv.org/abs/1234.5678</id>
                    <title>arXiv Paper</title>
                    <summary>arXiv abstract</summary>
                    <published>2024-01-15T00:00:00Z</published>
                    <author><name>John Doe</name></author>
                    <link href="http://arxiv.org/pdf/1234.5678.pdf" title="pdf"/>
                </entry>
            </feed>"""
            status_code = 200

            def raise_for_status(self):
                pass

        # Mock S2 response
        class MockS2Response:
            def json(self):
                return {
                    "data": [
                        {
                            "paperId": "s2-123",
                            "title": "S2 Paper",
                            "year": 2024,
                            "abstract": "S2 abstract",
                            "authors": [{"name": "Jane Doe"}],
                            "citationCount": 100,
                        }
                    ]
                }

            status_code = 200

            def raise_for_status(self):
                pass

        async def mock_get(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get("url", "")
            if "arxiv.org" in url:
                return MockArxivResponse()
            elif "semanticscholar.org" in url:
                return MockS2Response()
            return MockArxivResponse()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # Execute fusion search
        response = client.post(
            "/search/fusion",
            json={
                "query": "machine learning",
                "paper_ids": ["paper-1"],
                "limit": 20,
                "sources": ["library", "arxiv", "semantic_scholar"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "sources" in data
        assert "warnings" in data
        # Should have results from all sources
        assert len(data["results"]) > 0

    @pytest.mark.asyncio
    async def test_fusion_degradation_when_arxiv_fails(self, monkeypatch):
        """Test that fusion search continues when arXiv fails."""
        import httpx
        from app.core.multimodal_search_service import get_multimodal_search_service

        # Mock Milvus search
        class MockMultimodalService:
            async def search(self, **kwargs):
                return {"results": []}

        monkeypatch.setattr(
            "app.api.search.get_multimodal_search_service",
            lambda: MockMultimodalService()
        )

        # Mock arXiv failure
        class MockArxivFailure:
            async def raise_for_status(self):
                raise httpx.HTTPStatusError(
                    "Service unavailable",
                    request=None,
                    response=httpx.Response(503)
                )

        async def mock_get(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get("url", "")
            if "arxiv.org" in url:
                raise MockArxivFailure()
            # S2 succeeds
            class MockS2Response:
                def json(self):
                    return {"data": []}
                status_code = 200
                def raise_for_status(self):
                    pass
            return MockS2Response()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # Execute fusion search
        response = client.post(
            "/search/fusion",
            json={
                "query": "machine learning",
                "paper_ids": ["paper-1"],
                "limit": 20,
                "sources": ["library", "arxiv", "semantic_scholar"]
            }
        )

        # Should still return 200 (degradation)
        assert response.status_code == 200
        data = response.json()
        # Should have warning about arXiv failure
        assert len(data["warnings"]) > 0
        assert "arxiv" in data["warnings"][0].lower()

    @pytest.mark.asyncio
    async def test_fusion_deduplication(self, monkeypatch):
        """Test that fusion search deduplicates results by arXiv ID + title."""
        import httpx
        from app.core.multimodal_search_service import get_multimodal_search_service

        # Mock Milvus search
        class MockMultimodalService:
            async def search(self, **kwargs):
                return {"results": []}

        monkeypatch.setattr(
            "app.api.search.get_multimodal_search_service",
            lambda: MockMultimodalService()
        )

        # Both arXiv and S2 return same paper
        class MockArxivResponse:
            text = """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <entry>
                    <id>http://arxiv.org/abs/1234.5678</id>
                    <title>Duplicate Paper</title>
                    <summary>Duplicate abstract</summary>
                    <published>2024-01-15T00:00:00Z</published>
                    <author><name>John Doe</name></author>
                </entry>
            </feed>"""
            status_code = 200
            def raise_for_status(self):
                pass

        class MockS2Response:
            def json(self):
                return {
                    "data": [
                        {
                            "paperId": "s2-123",
                            "title": "Duplicate Paper",
                            "year": 2024,
                            "abstract": "Duplicate abstract",
                            "authors": [{"name": "John Doe"}],
                            "externalIds": {"ArXiv": "1234.5678"},
                            "citationCount": 100,
                        }
                    ]
                }
            status_code = 200
            def raise_for_status(self):
                pass

        async def mock_get(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get("url", "")
            if "arxiv.org" in url:
                return MockArxivResponse()
            elif "semanticscholar.org" in url:
                return MockS2Response()
            return MockArxivResponse()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # Execute fusion search
        response = client.post(
            "/search/fusion",
            json={
                "query": "machine learning",
                "paper_ids": [],
                "limit": 20,
                "sources": ["arxiv", "semantic_scholar"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Should deduplicate to 1 result (not 2)
        assert len(data["results"]) == 1
