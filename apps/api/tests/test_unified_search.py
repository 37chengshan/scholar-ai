"""
Tests for unified search functionality.

Tests merging, deduplication, filtering, and sorting of results
from multiple external sources (arXiv and Semantic Scholar).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List
from types import SimpleNamespace

from app.api.search import (
    search_unified,
    deduplicate_results,
    calculate_paper_score,
    SearchResult,
)


class TestUnifiedSearch:
    """Test suite for unified search endpoint."""

    @pytest.mark.asyncio
    async def test_unified_search_returns_both_sources(self):
        """
        Test 1: Unified search returns results from both sources.

        When searching unified, should get results from both arXiv
        and Semantic Scholar combined.
        """
        # Mock arXiv results
        arxiv_results = [
            SearchResult(
                id="2401.00001",
                title="Paper from arXiv",
                authors=["Author A"],
                year=2024,
                abstract="Abstract A...",
                source="arxiv",
                url="https://arxiv.org/abs/2401.00001",
                arxivId="2401.00001",
            )
        ]

        # Mock Semantic Scholar results
        s2_results = [
            SearchResult(
                id="s2-paper-1",
                title="Paper from S2",
                authors=["Author B"],
                year=2023,
                abstract="Abstract B...",
                source="semantic-scholar",
                url="https://www.semanticscholar.org/paper/s2-paper-1",
            )
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": arxiv_results}
            mock_s2.return_value = {"results": s2_results}

            result = await search_unified("test query", limit=10)

            assert "results" in result
            # Should have both papers (2 unique papers)
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_unified_search_arxiv_failure_returns_s2(self):
        """
        Test 2: When arXiv fails, S2 results are still returned.

        Error handling should allow partial results when one source fails.
        """
        s2_results = [
            SearchResult(
                id="s2-paper-1",
                title="S2 Only Paper",
                authors=["Author"],
                year=2024,
                abstract="Abstract...",
                source="semantic-scholar",
                url="https://www.semanticscholar.org/paper/s2-paper-1",
            )
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            # arXiv fails
            mock_arxiv.side_effect = Exception("arXiv API error")
            mock_s2.return_value = {"results": s2_results}

            result = await search_unified("test query", limit=10)

            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0].title == "S2 Only Paper"

    @pytest.mark.asyncio
    async def test_unified_search_s2_failure_returns_arxiv(self):
        """
        Test 3: When S2 fails, arXiv results are still returned.

        Error handling should allow partial results when one source fails.
        """
        arxiv_results = [
            SearchResult(
                id="2401.00001",
                title="arXiv Only Paper",
                authors=["Author"],
                year=2024,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/2401.00001",
                arxivId="2401.00001",
            )
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": arxiv_results}
            # S2 fails
            mock_s2.side_effect = Exception("S2 API error")

            result = await search_unified("test query", limit=10)

            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0].title == "arXiv Only Paper"

    @pytest.mark.asyncio
    async def test_unified_search_accepts_dict_results_from_adapters(self):
        """Unified search should normalize dict payloads before deduplication."""
        arxiv_results = [
            {
                "id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani"],
                "year": 2017,
                "abstract": "Transformer paper",
                "source": "arxiv",
                "url": "https://arxiv.org/abs/1706.03762",
                "arxivId": "1706.03762",
            }
        ]
        s2_results = [
            {
                "id": "s2-paper-1",
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "year": 2017,
                "abstract": "Transformer paper with richer metadata",
                "source": "semantic-scholar",
                "url": "https://www.semanticscholar.org/paper/s2-paper-1",
                "arxivId": "1706.03762",
                "citationCount": 1000,
            }
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": arxiv_results}
            mock_s2.return_value = {"results": s2_results}

            result = await search_unified("Attention Is All You Need", limit=10)

            assert len(result["results"]) == 1
            assert isinstance(result["results"][0], SearchResult)
            assert result["results"][0].source == "semantic-scholar"

    @pytest.mark.asyncio
    async def test_year_from_filter_excludes_older_papers(self):
        """
        Test 4: year_from filter excludes papers before specified year.

        Papers from years before year_from should not be in results.
        """
        all_results = [
            SearchResult(
                id="old-paper",
                title="Old Paper 2010",
                authors=["Author"],
                year=2010,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/old",
                arxivId="old",
            ),
            SearchResult(
                id="new-paper",
                title="New Paper 2024",
                authors=["Author"],
                year=2024,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/new",
                arxivId="new",
            ),
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": all_results}
            mock_s2.return_value = {"results": []}

            # Filter from 2020
            result = await search_unified("test", limit=10, year_from=2020)

            assert len(result["results"]) == 1
            assert result["results"][0].year >= 2020
            assert result["results"][0].title == "New Paper 2024"

    @pytest.mark.asyncio
    async def test_year_to_filter_excludes_newer_papers(self):
        """
        Test 5: year_to filter excludes papers after specified year.

        Papers from years after year_to should not be in results.
        """
        all_results = [
            SearchResult(
                id="old-paper",
                title="Old Paper 2010",
                authors=["Author"],
                year=2010,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/old",
                arxivId="old",
            ),
            SearchResult(
                id="new-paper",
                title="New Paper 2024",
                authors=["Author"],
                year=2024,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/new",
                arxivId="new",
            ),
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": all_results}
            mock_s2.return_value = {"results": []}

            # Filter to 2015
            result = await search_unified("test", limit=10, year_to=2015)

            assert len(result["results"]) == 1
            assert result["results"][0].year <= 2015
            assert result["results"][0].title == "Old Paper 2010"

    @pytest.mark.asyncio
    async def test_results_sorted_by_citation_score(self):
        """
        Test 6: Results are sorted by citation score (highest first).

        Papers with more citations should appear first.
        """
        # Create papers with different citation counts
        papers = [
            SearchResult(
                id="low-citations",
                title="Low Citations",
                authors=["Author"],
                year=2020,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/low",
                citationCount=10,
                arxivId="low",
            ),
            SearchResult(
                id="high-citations",
                title="High Citations",
                authors=["Author"],
                year=2020,
                abstract="Abstract...",
                source="semantic-scholar",
                url="https://s2/paper/high",
                citationCount=1000,
            ),
            SearchResult(
                id="medium-citations",
                title="Medium Citations",
                authors=["Author"],
                year=2020,
                abstract="Abstract...",
                source="semantic-scholar",
                url="https://s2/paper/med",
                citationCount=100,
            ),
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": [papers[0]]}
            mock_s2.return_value = {"results": [papers[1], papers[2]]}

            result = await search_unified("test", limit=10)

            # Should be sorted by citation score (highest first)
            titles = [r.title for r in result["results"]]
            assert titles[0] == "High Citations"
            assert titles[1] == "Medium Citations"
            assert titles[2] == "Low Citations"

    @pytest.mark.asyncio
    async def test_limit_parameter_limits_results(self):
        """
        Test 7: Limit parameter correctly limits result count.

        When limit=5, should return at most 5 results.
        """
        # Create 10 papers
        many_papers = [
            SearchResult(
                id=f"paper-{i}",
                title=f"Paper {i}",
                authors=["Author"],
                year=2024,
                abstract="Abstract...",
                source="arxiv",
                url=f"https://arxiv.org/abs/{i}",
                arxivId=f"{i}",
            )
            for i in range(10)
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": many_papers[:5]}
            mock_s2.return_value = {"results": many_papers[5:]}

            # Limit to 3
            result = await search_unified("test", limit=3)

            assert len(result["results"]) <= 3

    @pytest.mark.asyncio
    async def test_duplicate_arxiv_id_appears_once(self):
        """
        Test 8: Duplicate papers (same arXiv ID) appear only once.

        When the same paper appears in both sources, it should be
        deduplicated and appear only once.
        """
        # Same paper from both sources
        arxiv_paper = SearchResult(
            id="2401.12345",
            title="Same Paper Title",
            authors=["Author A"],
            year=2024,
            abstract="Abstract...",
            source="arxiv",
            url="https://arxiv.org/abs/2401.12345",
            arxivId="2401.12345",
        )

        s2_paper = SearchResult(
            id="s2-id",
            title="Same Paper Title",
            authors=["Author A", "Author B"],  # S2 has more metadata
            year=2024,
            abstract="Abstract...",
            source="semantic-scholar",
            url="https://www.semanticscholar.org/paper/s2-id",
            arxivId="2401.12345",  # Same arXiv ID
        )

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": [arxiv_paper]}
            mock_s2.return_value = {"results": [s2_paper]}

            result = await search_unified("test", limit=10)

            # Should only have 1 unique paper
            assert len(result["results"]) == 1
            # Should prefer S2 result (more metadata)
            assert result["results"][0].source == "semantic-scholar"

    @pytest.mark.asyncio
    async def test_route_unified_search_includes_internal_filename_fallback_results(self):
        """Route-level unified search should surface known in-library filename fallback hits."""
        from app.api.search.library import search_unified as route_search_unified

        paper = SimpleNamespace(
            id="paper-1",
            title="test_5_pages",
            authors=[],
            year=None,
            abstract=None,
            doi=None,
            arxiv_id=None,
            s2_paper_id=None,
            pdf_url=None,
            venue=None,
            citations=None,
            status="completed",
        )
        task = SimpleNamespace(status="completed")
        user = SimpleNamespace(id="user-1")

        with patch('app.api.search.library.get_search_cache', new=AsyncMock(return_value=None)), \
             patch('app.api.search.library.set_search_cache', new=AsyncMock()), \
             patch('app.api.search.library.search_arxiv', new=AsyncMock(return_value={"results": [], "total": 0})), \
             patch('app.api.search.library.search_semantic_scholar', new=AsyncMock(return_value={"results": [], "total": 0})), \
             patch('app.api.search.library.PaperService.search_papers_for_api', new=AsyncMock(return_value={
                 "papers": [paper],
                 "task_map": {"paper-1": task},
                 "chunk_count_map": {"paper-1": 12},
                 "total": 1,
                 "page": 1,
                 "limit": 20,
                 "total_pages": 1,
                 "query": "test_5_pages",
             })):

            result = await route_search_unified(
                query="test_5_pages",
                limit=20,
                offset=0,
                year_from=None,
                year_to=None,
                db=MagicMock(),
                optional_user=user,
            )

            assert result.success is True
            payload = result.data
            assert payload["total"] == 1
            assert len(payload["results"]) == 1
            assert payload["results"][0]["source"] == "internal"
            assert payload["results"][0]["title"] == "test_5_pages"
            assert payload["results"][0]["libraryStatus"] == "imported_fulltext_ready"


class TestUnifiedSearchErrorHandling:
    """Test error handling in unified search."""

    @pytest.mark.asyncio
    async def test_both_sources_fail_returns_empty(self):
        """
        Test that when both sources fail, empty results are returned.

        Graceful degradation - don't crash when external APIs fail.
        """
        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.side_effect = Exception("arXiv error")
            mock_s2.side_effect = Exception("S2 error")

            result = await search_unified("test", limit=10)

            assert "results" in result
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_invalid_year_filter_ignored(self):
        """
        Test that invalid year filters don't break search.

        Edge case: year_from > year_to should still work.
        """
        papers = [
            SearchResult(
                id="paper-1",
                title="Paper",
                authors=["Author"],
                year=2020,
                abstract="Abstract...",
                source="arxiv",
                url="https://arxiv.org/abs/1",
                arxivId="1",
            ),
        ]

        with patch('app.api.search.search_arxiv') as mock_arxiv, \
             patch('app.api.search.search_semantic_scholar') as mock_s2:

            mock_arxiv.return_value = {"results": papers}
            mock_s2.return_value = {"results": []}

            # year_from > year_to (invalid range)
            result = await search_unified("test", limit=10, year_from=2025, year_to=2020)

            # Should return empty due to conflicting filters
            assert len(result["results"]) == 0
