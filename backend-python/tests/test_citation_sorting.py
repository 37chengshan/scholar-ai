"""
Tests for citation-based paper ranking and sorting.

Tests the calculate_paper_score function which combines:
- Citation score (log-scaled, capped at 1.0 for >100K citations)
- Recency score (exponential decay with 10-year half-life)
- Relevance score (provided by search API)

Formula: score = citation_score * 0.5 + recency_score * 0.3 + relevance * 0.2
"""

import math
from datetime import datetime

import pytest


class TestCalculatePaperScore:
    """Test suite for paper scoring function."""

    @pytest.fixture
    def calculate_paper_score(self):
        """Import the scoring function."""
        from app.api.search import calculate_paper_score
        return calculate_paper_score

    def test_highly_cited_vs_low_cited_paper(self, calculate_paper_score):
        """Test 1: Paper with 1000 citations in 2020 gets higher score than paper with 10 citations in 2024.

        High citation count should outweigh recency advantage.
        """
        paper_2020_high_citations = calculate_paper_score(
            citation_count=1000,
            year=2020,
            relevance=0.5
        )

        paper_2024_low_citations = calculate_paper_score(
            citation_count=10,
            year=2024,
            relevance=0.5
        )

        # The highly cited paper should have higher score despite being older
        assert paper_2020_high_citations > paper_2024_low_citations, \
            f"Highly cited 2020 paper ({paper_2020_high_citations}) should score higher than low-cited 2024 paper ({paper_2024_low_citations})"

    def test_recency_scoring(self, calculate_paper_score):
        """Test 2: Paper from 2024 gets higher recency_score than paper from 2010.

        More recent papers should have higher recency component.
        """
        paper_2024 = calculate_paper_score(
            citation_count=0,
            year=2024,
            relevance=0.5
        )

        paper_2010 = calculate_paper_score(
            citation_count=0,
            year=2010,
            relevance=0.5
        )

        # With same citations and relevance, recent paper should score higher
        assert paper_2024 > paper_2010, \
            f"2024 paper ({paper_2024}) should score higher than 2010 paper ({paper_2010})"

    def test_citation_score_caps_at_1(self, calculate_paper_score):
        """Test 3: Citation score caps at 1.0 for papers with >100K citations.

        log10(100000 + 1) / 5 = log10(100001) / 5 ≈ 5.0 / 5 = 1.0
        """
        paper_100k = calculate_paper_score(
            citation_count=100000,
            year=2020,
            relevance=0.5
        )

        paper_1m = calculate_paper_score(
            citation_count=1000000,
            year=2020,
            relevance=0.5
        )

        # Both should have citation_score = 1.0 (the maximum)
        # So final scores should be very close (only recency differs by year, same here)
        assert abs(paper_100k - paper_1m) < 0.001, \
            f"Papers with 100K and 1M citations should have similar scores ({paper_100k} vs {paper_1m})"

    def test_score_formula_weights(self, calculate_paper_score):
        """Test 4: Final score is weighted combination (0.5 citation + 0.3 recency + 0.2 relevance).

        Verify the formula produces expected values.
        """
        current_year = datetime.now().year

        # Test with 0 citations, current year, 0.5 relevance
        # citation_score = 0, recency_score = 1.0, relevance = 0.5
        # expected = 0 * 0.5 + 1.0 * 0.3 + 0.5 * 0.2 = 0.3 + 0.1 = 0.4
        score = calculate_paper_score(
            citation_count=0,
            year=current_year,
            relevance=0.5
        )

        # Allow small floating point tolerance
        assert abs(score - 0.4) < 0.001, f"Expected score ~0.4 for (0 citations, current year, 0.5 relevance), got {score}"

        # Test with citations that give citation_score = 0.5
        # log10(citations + 1) / 5 = 0.5 => log10(citations + 1) = 2.5 => citations ≈ 315
        # citation_score = 0.5, recency_score = 1.0, relevance = 0.5
        # expected = 0.5 * 0.5 + 1.0 * 0.3 + 0.5 * 0.2 = 0.25 + 0.3 + 0.1 = 0.65
        score_with_citations = calculate_paper_score(
            citation_count=315,  # Should give citation_score ≈ 0.5
            year=current_year,
            relevance=0.5
        )

        assert abs(score_with_citations - 0.65) < 0.05, \
            f"Expected score ~0.65 for (315 citations, current year, 0.5 relevance), got {score_with_citations}"

    def test_sorting_by_score(self, calculate_paper_score):
        """Test 5: Sorting by score produces correct order for mixed citation/recency papers.

        Create several papers with different combinations and verify sorting.
        """
        papers = [
            {"title": "Very Old, Highly Cited", "citation_count": 50000, "year": 1990, "expected_rank": 2},
            {"title": "Recent, Low Cited", "citation_count": 10, "year": 2024, "expected_rank": 3},
            {"title": "Recent, Highly Cited", "citation_count": 1000, "year": 2024, "expected_rank": 1},
            {"title": "Old, Low Cited", "citation_count": 5, "year": 2000, "expected_rank": 4},
        ]

        # Calculate scores
        for paper in papers:
            paper["score"] = calculate_paper_score(
                citation_count=paper["citation_count"],
                year=paper["year"],
                relevance=0.5
            )

        # Sort by score descending
        sorted_papers = sorted(papers, key=lambda x: x["score"], reverse=True)

        # Verify expected ranking
        for i, paper in enumerate(sorted_papers, 1):
            assert paper["expected_rank"] == i, \
                f"Paper '{paper['title']}' expected rank {paper['expected_rank']}, got rank {i} (score: {paper['score']})"

    def test_none_citation_count(self, calculate_paper_score):
        """Test that None citation_count is handled as 0."""
        score_none = calculate_paper_score(
            citation_count=None,
            year=2024,
            relevance=0.5
        )

        score_zero = calculate_paper_score(
            citation_count=0,
            year=2024,
            relevance=0.5
        )

        assert score_none == score_zero, \
            f"None and 0 citations should produce same score ({score_none} vs {score_zero})"

    def test_relevance_parameter(self, calculate_paper_score):
        """Test that relevance parameter affects the final score."""
        low_relevance = calculate_paper_score(
            citation_count=100,
            year=2024,
            relevance=0.1
        )

        high_relevance = calculate_paper_score(
            citation_count=100,
            year=2024,
            relevance=0.9
        )

        assert high_relevance > low_relevance, \
            f"Higher relevance should produce higher score ({high_relevance} vs {low_relevance})"

    def test_recency_decay_calculation(self, calculate_paper_score):
        """Test recency score follows exponential decay with 10-year half-life."""
        current_year = datetime.now().year

        # Current year should have recency_score = 1.0 (exp(0) = 1)
        score_current = calculate_paper_score(
            citation_count=0,
            year=current_year,
            relevance=0.0  # Isolate recency component
        )

        # 10 years ago should have recency_score = exp(-1) ≈ 0.368
        score_10yr = calculate_paper_score(
            citation_count=0,
            year=current_year - 10,
            relevance=0.0
        )

        # With relevance=0, score = 0 * 0.5 + recency * 0.3 + 0 * 0.2 = recency * 0.3
        expected_current = 0.3  # 1.0 * 0.3
        expected_10yr = 0.3 * math.exp(-1)  # exp(-1) * 0.3

        assert abs(score_current - expected_current) < 0.001, \
            f"Current year recency contribution should be {expected_current}, got {score_current}"

        assert abs(score_10yr - expected_10yr) < 0.01, \
            f"10-year recency contribution should be ~{expected_10yr:.3f}, got {score_10yr}"


class TestScoreFunctionEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def calculate_paper_score(self):
        """Import the scoring function."""
        from app.api.search import calculate_paper_score
        return calculate_paper_score

    def test_future_year(self, calculate_paper_score):
        """Test handling of future years (should be treated as current)."""
        current_year = datetime.now().year

        # Future year should get same score as current year
        # (year_diff = max(0, current_year - year) would be 0 for future years if max is applied)
        score_future = calculate_paper_score(
            citation_count=0,
            year=current_year + 5,
            relevance=0.5
        )

        score_current = calculate_paper_score(
            citation_count=0,
            year=current_year,
            relevance=0.5
        )

        # Both should have same recency score
        assert abs(score_future - score_current) < 0.001, \
            f"Future year should be treated same as current ({score_future} vs {score_current})"

    def test_single_citation(self, calculate_paper_score):
        """Test scoring with single citation."""
        score = calculate_paper_score(
            citation_count=1,
            year=datetime.now().year,
            relevance=0.5
        )

        # citation_score = log10(1 + 1) / 5 = log10(2) / 5 ≈ 0.06
        # recency_score = 1.0
        # final = 0.06 * 0.5 + 1.0 * 0.3 + 0.5 * 0.2 ≈ 0.03 + 0.3 + 0.1 = 0.43
        assert score > 0.4, f"Single citation paper should score > 0.4, got {score}"
        assert score < 0.5, f"Single citation paper should score < 0.5, got {score}"
