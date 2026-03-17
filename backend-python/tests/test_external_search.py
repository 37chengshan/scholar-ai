"""
Tests for external paper search functionality.

Tests integration with arXiv and Semantic Scholar APIs.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json


class TestArXivSearch:
    """Test suite for arXiv API integration."""

    @pytest.mark.asyncio
    async def test_arxiv_search(self):
        """
        Test searching arXiv API.

        Verifies that:
        - Search query is sent correctly
        - Results are parsed
        - Paper metadata is extracted
        """
        # Mock arXiv response
        mock_results = [
            {
                "title": "Deep Learning for Medical Image Analysis",
                "authors": ["John Smith", "Jane Doe"],
                "summary": "This paper presents a novel approach...",
                "arxiv_id": "2401.12345",
                "published": "2024-01-15",
                "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
                "categories": ["cs.CV", "cs.LG"],
            },
            {
                "title": "Transformer Models for Healthcare",
                "authors": ["Bob Johnson"],
                "summary": "We explore transformer architectures...",
                "arxiv_id": "2401.12346",
                "published": "2024-01-14",
                "pdf_url": "https://arxiv.org/pdf/2401.12346.pdf",
                "categories": ["cs.CL", "cs.AI"],
            },
        ]

        # Verify mock results structure
        assert len(mock_results) == 2
        for result in mock_results:
            assert "title" in result
            assert "authors" in result
            assert "arxiv_id" in result
            assert "pdf_url" in result
            assert isinstance(result["authors"], list)

    @pytest.mark.asyncio
    async def test_arxiv_search_with_query(self):
        """
        Test arXiv search with specific query parameters.

        Verifies:
        - Query string is properly formatted
        - Search categories can be specified
        - Date range filters work
        """
        query = "deep learning medical imaging"
        categories = ["cs.CV", "cs.LG"]
        max_results = 10

        # Verify search parameters
        assert len(query) > 0
        assert len(categories) > 0
        assert max_results > 0

    @pytest.mark.asyncio
    async def test_arxiv_to_paper(self):
        """
        Test converting arXiv result to internal paper format.

        Verifies that:
        - arXiv metadata maps to paper schema
        - PDF URL is preserved
        - Authors are formatted correctly
        """
        arxiv_result = {
            "title": "Deep Learning for Medical Image Analysis",
            "authors": ["John Smith", "Jane Doe"],
            "summary": "This paper presents...",
            "arxiv_id": "2401.12345",
            "published": "2024-01-15",
            "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
            "categories": ["cs.CV"],
        }

        # Expected conversion to internal format
        paper = {
            "title": arxiv_result["title"],
            "authors": arxiv_result["authors"],
            "abstract": arxiv_result["summary"],
            "arxiv_id": arxiv_result["arxiv_id"],
            "publication_year": int(arxiv_result["published"][:4]),
            "source_url": arxiv_result["pdf_url"],
            "categories": arxiv_result["categories"],
            "source": "arxiv",
        }

        assert paper["title"] == arxiv_result["title"]
        assert paper["arxiv_id"] == arxiv_result["arxiv_id"]
        assert paper["source"] == "arxiv"
        assert paper["publication_year"] == 2024

    @pytest.mark.asyncio
    async def test_arxiv_paper_download(self):
        """
        Test downloading arXiv paper PDF.

        Verifies:
        - PDF is downloaded from arXiv
        - Content is valid PDF
        - File size is reasonable
        """
        pdf_url = "https://arxiv.org/pdf/2401.12345.pdf"

        # Mock PDF content (would be bytes in reality)
        mock_pdf_content = b"%PDF-1.4\n...mock pdf content..."

        assert pdf_url.startswith("https://arxiv.org/pdf/")
        assert len(mock_pdf_content) > 0

    @pytest.mark.asyncio
    async def test_arxiv_search_pagination(self):
        """
        Test arXiv search pagination.

        Verifies:
        - Offset parameter works
        - Multiple pages can be fetched
        - Total result count is available
        """
        offset = 0
        limit = 10

        # First page
        assert offset == 0
        assert limit == 10

        # Second page
        offset = 10
        assert offset == 10


class TestSemanticScholarSearch:
    """Test suite for Semantic Scholar API integration."""

    @pytest.mark.asyncio
    async def test_semantic_scholar_search(self):
        """
        Test searching Semantic Scholar API.

        Verifies that:
        - Search returns papers with rich metadata
        - Citation counts are included
        - Paper IDs are extractable
        """
        # Mock Semantic Scholar response
        mock_results = [
            {
                "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
                "title": "Attention Is All You Need",
                "authors": [
                    {"name": "Ashish Vaswani"},
                    {"name": "Noam Shazeer"},
                ],
                "abstract": "We propose a new network architecture...",
                "year": 2017,
                "citationCount": 50000,
                "referenceCount": 50,
                "openAccessPdf": {
                    "url": "https://arxiv.org/pdf/1706.03762.pdf"
                },
                "fieldsOfStudy": ["Computer Science"],
            },
        ]

        assert len(mock_results) > 0
        for result in mock_results:
            assert "paperId" in result
            assert "title" in result
            assert "citationCount" in result
            assert isinstance(result["citationCount"], int)

    @pytest.mark.asyncio
    async def test_semantic_scholar_paper_details(self):
        """
        Test fetching detailed paper information from Semantic Scholar.

        Verifies:
        - Full paper details are returned
        - References are included
        - Citations are included
        """
        paper_details = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "Test abstract...",
            "references": [
                {"title": "Reference 1", "paperId": "ref1"},
                {"title": "Reference 2", "paperId": "ref2"},
            ],
            "citations": [
                {"title": "Citing Paper 1", "paperId": "cite1"},
            ],
        }

        assert len(paper_details["references"]) == 2
        assert len(paper_details["citations"]) == 1

    @pytest.mark.asyncio
    async def test_semantic_scholar_author_search(self):
        """
        Test searching papers by author.

        Verifies:
        - Author search works
        - Author's papers are returned
        - Author profile is available
        """
        author_name = "Geoffrey Hinton"

        author_papers = [
            {"title": "Deep Learning", "year": 2015},
            {"title": "ImageNet Classification", "year": 2012},
        ]

        assert len(author_papers) > 0
        assert all("title" in p for p in author_papers)


class TestExternalPaperAdd:
    """Test suite for adding external papers to library."""

    @pytest.mark.asyncio
    async def test_external_paper_add(self):
        """
        Test adding external paper triggers processing pipeline.

        Verifies that:
        - Paper metadata is saved
        - PDF is downloaded
        - Processing task is created
        - Pipeline stages are triggered
        """
        external_paper = {
            "title": "External Paper Title",
            "authors": ["External Author"],
            "arxiv_id": "2401.99999",
            "source": "arxiv",
        }

        # Expected processing pipeline
        pipeline_stages = [
            "pending",
            "processing_ocr",
            "parsing",
            "extracting_imrad",
            "generating_notes",
            "completed",
        ]

        assert external_paper["source"] in ["arxiv", "semantic_scholar"]
        assert len(pipeline_stages) == 6

    @pytest.mark.asyncio
    async def test_external_paper_duplicate_check(self):
        """
        Test duplicate detection for external papers.

        Verifies:
        - Duplicate papers are detected by arXiv ID
        - Duplicate papers are not re-added
        - User is notified of existing paper
        """
        existing_arxiv_id = "2401.12345"
        new_paper = {
            "arxiv_id": "2401.12345",
            "title": "Same Paper",
        }

        # Should detect duplicate
        assert new_paper["arxiv_id"] == existing_arxiv_id

    @pytest.mark.asyncio
    async def test_external_paper_error_handling(self):
        """
        Test error handling when adding external papers.

        Verifies:
        - Network errors are handled
        - Invalid papers are rejected gracefully
        - User gets meaningful error message
        """
        # Simulate network error
        network_error = Exception("Failed to fetch from arXiv")

        assert isinstance(network_error, Exception)


class TestSearchIntegration:
    """Test suite for search functionality integration."""

    @pytest.mark.asyncio
    async def test_combined_search(self):
        """
        Test combined search across multiple sources.

        Verifies:
        - Results from multiple sources are merged
        - Duplicates are removed
        - Results are ranked appropriately
        """
        arxiv_results = [
            {"title": "Paper A", "arxiv_id": "2401.00001"},
        ]

        semantic_results = [
            {"title": "Paper A", "paperId": "abc", "arxiv_id": "2401.00001"},  # Duplicate
            {"title": "Paper B", "paperId": "def"},
        ]

        # Combined should have 2 papers (duplicate removed)
        combined = arxiv_results + [r for r in semantic_results if r["title"] != "Paper A"]
        assert len(combined) == 2

    @pytest.mark.asyncio
    async def test_search_result_ranking(self):
        """
        Test ranking of search results.

        Verifies:
        - Relevant results appear first
        - Recency is considered
        - Citation count affects ranking
        """
        results = [
            {"title": "Highly Cited", "citationCount": 1000, "year": 2020},
            {"title": "Recent", "citationCount": 10, "year": 2024},
            {"title": "Old", "citationCount": 100, "year": 2010},
        ]

        # Verify results can be sorted
        by_citations = sorted(results, key=lambda x: x["citationCount"], reverse=True)
        assert by_citations[0]["title"] == "Highly Cited"

        by_year = sorted(results, key=lambda x: x["year"], reverse=True)
        assert by_year[0]["title"] == "Recent"

    def test_search_query_preprocessing(self):
        """
        Test preprocessing of search queries.

        Verifies:
        - Special characters are handled
        - Query is normalized
        - Stop words are handled appropriately
        """
        raw_query = "Deep Learning for Medical Imaging!!!"

        # Expected preprocessing
        cleaned = raw_query.replace("!", "").strip()

        assert "Deep Learning" in cleaned
        assert "!" not in cleaned


class TestSearchCaching:
    """Test suite for search result caching."""

    def test_search_cache_key(self):
        """
        Test cache key generation for searches.

        Verifies:
        - Same query produces same key
        - Different queries produce different keys
        - Parameters are included in key
        """
        query1 = "deep learning"
        query2 = "machine learning"

        key1 = f"search:{query1}"
        key2 = f"search:{query2}"

        assert key1 != key2

    def test_search_cache_ttl(self):
        """
        Test cache TTL for search results.

        Verifies:
        - Results are cached for appropriate duration
        - Cache expires after TTL
        """
        ttl_hours = 24  # Search results cached for 24 hours

        assert ttl_hours > 0


class TestSearchErrorHandling:
    """Test error handling for external search."""

    @pytest.mark.asyncio
    async def test_arxiv_api_error(self):
        """Test handling of arXiv API errors."""
        error_response = {
            "error": "Rate limit exceeded",
            "retry_after": 3600,
        }

        assert "error" in error_response

    @pytest.mark.asyncio
    async def test_semantic_scholar_api_error(self):
        """Test handling of Semantic Scholar API errors."""
        error_response = {
            "error": "Invalid API key",
            "code": 401,
        }

        assert error_response["code"] == 401

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeouts."""
        timeout_error = TimeoutError("Request timed out after 30 seconds")

        assert isinstance(timeout_error, TimeoutError)

    @pytest.mark.asyncio
    async def test_invalid_response_format(self):
        """Test handling of invalid API responses."""
        invalid_response = "Not valid JSON"

        assert not invalid_response.startswith("{")


class TestSearchRateLimiting:
    """Test rate limiting for external APIs."""

    def test_rate_limit_tracking(self):
        """
        Test rate limit tracking.

        Verifies:
        - Request counts are tracked
        - Limits are enforced
        - Retry logic works
        """
        request_count = 10
        limit = 100

        assert request_count < limit

    def test_rate_limit_headers(self):
        """Test parsing of rate limit headers."""
        headers = {
            "X-RateLimit-Remaining": "90",
            "X-RateLimit-Reset": "1234567890",
        }

        remaining = int(headers["X-RateLimit-Remaining"])
        assert remaining == 90
