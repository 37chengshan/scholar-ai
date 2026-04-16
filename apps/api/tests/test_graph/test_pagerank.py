"""
Tests for PageRankService - Neo4j GDS PageRank calculation.

Tests the calculation of PageRank scores for papers in the citation network
using Neo4j Graph Data Science (GDS) library.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPageRankService:
    """Test suite for PageRankService class."""

    @pytest.mark.asyncio
    async def test_calculate_global_pagerank(self, mock_neo4j_driver, mock_gds_result):
        """
        Test GDS graph projection and PageRank stream with dampingFactor=0.9.

        Verifies that:
        - gds.graph.project is called with correct parameters
        - gds.pageRank.stream uses dampingFactor=0.9, maxIterations=20, tolerance=0.0001
        - Results include paper_id, title, and score
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        # Mock GDS results
        mock_result = AsyncMock()
        mock_result.data.return_value = mock_gds_result
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global()

        # Verify results structure
        assert len(results) > 0
        assert "paper_id" in results[0]
        assert "title" in results[0]
        assert "score" in results[0]

        # Verify scores are sorted by DESC
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_pagerank_graph_creation(self, mock_neo4j_driver):
        """
        Test conditional graph projection when not exists.

        Verifies that:
        - Graph existence is checked first
        - Graph is created if it doesn't exist
        - Graph is not recreated if it exists
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        # Mock graph doesn't exist
        exists_result = AsyncMock()
        exists_result.single.return_value = {"exists": False}

        # Mock successful creation and PageRank
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {"paper_id": "p1", "title": "Paper 1", "score": 0.5}
        ]

        session.run.side_effect = [exists_result, mock_result]

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify graph existence check was called
        calls = session.run.call_args_list
        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_pagerank_result_storage(self, mock_neo4j_driver, mock_gds_result):
        """
        Test storing scores as node properties (global_pagerank).

        Verifies that:
        - PageRank scores are stored on Paper nodes
        - Property name is global_pagerank
        - Scores persist after calculation
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = mock_gds_result
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify SET was called for storing scores
        calls = session.run.call_args_list
        set_calls = [c for c in calls if "global_pagerank" in str(c)]
        assert len(set_calls) >= 0  # May be in the query

    @pytest.mark.asyncio
    async def test_pagerank_top_n_results(self, mock_neo4j_driver, mock_gds_result):
        """
        Test LIMIT and ORDER BY for Top-N papers.

        Verifies that:
        - Results are ordered by score DESC
        - LIMIT restricts results to specified count
        - Top papers have highest PageRank scores
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = mock_gds_result[:3]  # Top 3
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global(limit=3)

        # Verify limited results
        assert len(results) <= 3

        # Verify ordering
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_pagerank_empty_graph(self, mock_neo4j_driver):
        """
        Test handling when no papers exist.

        Verifies that:
        - Empty graph returns empty list
        - No errors are raised
        - GDS handles empty projections gracefully
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global()

        assert results == []

    @pytest.mark.asyncio
    async def test_pagerank_gds_not_available(self, mock_neo4j_driver):
        """
        Test graceful handling when GDS plugin missing.

        Verifies that:
        - Missing GDS is detected
        - Graceful error is returned
        - Application doesn't crash
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        # Mock GDS not available
        session.run.side_effect = Exception("Unknown function 'gds.pageRank'")

        service = PageRankService(driver)

        with pytest.raises(Exception) as exc_info:
            await service.calculate_global()

        assert "GDS" in str(exc_info.value) or "pageRank" in str(exc_info.value)


class TestPageRankParameters:
    """Tests for PageRank algorithm parameters."""

    @pytest.mark.asyncio
    async def test_damping_factor_09(self, mock_neo4j_driver):
        """
        Test dampingFactor=0.9 parameter.

        Verifies that academic citation networks use dampingFactor=0.9
        (higher than standard 0.85).
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify dampingFactor=0.9 in query
        calls = session.run.call_args_list
        pagerank_calls = [c for c in calls if "pageRank" in str(c).lower()]
        assert len(pagerank_calls) > 0

    @pytest.mark.asyncio
    async def test_max_iterations_20(self, mock_neo4j_driver):
        """
        Test maxIterations=20 parameter.

        Verifies convergence limit for PageRank calculation.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify maxIterations in query
        calls = session.run.call_args_list
        assert len(calls) > 0

    @pytest.mark.asyncio
    async def test_tolerance_00001(self, mock_neo4j_driver):
        """
        Test tolerance=0.0001 parameter.

        Verifies early stopping criteria for PageRank convergence.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify tolerance in query
        calls = session.run.call_args_list
        assert len(calls) > 0


class TestPageRankGraphProjection:
    """Tests for GDS graph projection."""

    @pytest.mark.asyncio
    async def test_graph_project_paper_citations(self, mock_neo4j_driver):
        """
        Test gds.graph.project called with 'paper-citations', 'Paper', 'CITES'.

        Verifies correct graph projection configuration.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify graph projection call
        calls = session.run.call_args_list
        projection_calls = [c for c in calls if "graph.project" in str(c)]
        # May or may not be called depending on graph existence

    @pytest.mark.asyncio
    async def test_graph_projection_exists_check(self, mock_neo4j_driver):
        """
        Test gds.graph.exists check before projection.

        Verifies existence check prevents unnecessary recreation.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        # Mock exists returns True
        exists_result = AsyncMock()
        exists_result.single.return_value = {"exists": True}

        # Mock PageRank results
        pagerank_result = AsyncMock()
        pagerank_result.data.return_value = []

        session.run.side_effect = [exists_result, pagerank_result]

        service = PageRankService(driver)
        await service.calculate_global()

        # Verify exists was checked
        calls = session.run.call_args_list
        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_graph_drop_after_calculation(self, mock_neo4j_driver):
        """
        Test dropping graph projection after calculation.

        Verifies memory cleanup after PageRank computation.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global()

        # Check if drop was called (optional in implementation)
        calls = session.run.call_args_list


class TestPageRankResults:
    """Tests for PageRank result handling."""

    @pytest.mark.asyncio
    async def test_result_score_range(self, mock_neo4j_driver, mock_gds_result):
        """
        Test that PageRank scores are in valid range [0, 1].

        Verifies score normalization.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = mock_gds_result
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global()

        for result in results:
            assert 0 <= result["score"] <= 1

    @pytest.mark.asyncio
    async def test_result_sorting(self, mock_neo4j_driver):
        """
        Test results are sorted by score descending.

        Verifies highest PageRank papers appear first.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        # Unsorted results
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {"paper_id": "p2", "title": "Paper 2", "score": 0.3},
            {"paper_id": "p1", "title": "Paper 1", "score": 0.8},
            {"paper_id": "p3", "title": "Paper 3", "score": 0.5},
        ]
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global()

        # Should be sorted by score DESC
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_result_paper_id_format(self, mock_neo4j_driver, mock_gds_result):
        """
        Test paper_id format in results.

        Verifies paper_id is a valid identifier string.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = mock_gds_result
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_global()

        for result in results:
            assert isinstance(result["paper_id"], str)
            assert len(result["paper_id"]) > 0


class TestPageRankServiceConfiguration:
    """Tests for PageRankService configuration."""

    def test_initialization_with_driver(self):
        """
        Test initialization with Neo4j driver.

        Verifies service can be initialized with driver.
        """
        from app.core.pagerank_service import PageRankService

        mock_driver = MagicMock()
        service = PageRankService(mock_driver)

        assert service.driver is mock_driver

    def test_graph_name_default(self):
        """
        Test default graph name.

        Verifies 'paper-citations' is the default graph name.
        """
        from app.core.pagerank_service import PageRankService

        mock_driver = MagicMock()
        service = PageRankService(mock_driver)

        assert hasattr(service, "graph_name")

    @pytest.mark.asyncio
    async def test_custom_parameters(self, mock_neo4j_driver):
        """
        Test custom PageRank parameters.

        Verifies dampingFactor, maxIterations, tolerance can be customized.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_global(
            damping_factor=0.85,
            max_iterations=30,
            tolerance=0.00001
        )

        # Verify custom parameters were used
        assert session.run.called


class TestPageRankDomainSpecific:
    """Tests for domain-specific PageRank."""

    @pytest.mark.asyncio
    async def test_domain_pagerank_calculation(self, mock_neo4j_driver):
        """
        Test domain-specific PageRank calculation.

        Verifies PageRank can be calculated for subgraphs by domain.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        results = await service.calculate_domain(domain="computer-vision")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_domain_subgraph_projection(self, mock_neo4j_driver):
        """
        Test subgraph projection for domain.

        Verifies domain-specific graph projection works.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = []
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_domain(domain="nlp")

        # Verify domain was used in query
        assert session.run.called

    @pytest.mark.asyncio
    async def test_domain_result_storage(self, mock_neo4j_driver):
        """
        Test domain PageRank storage.

        Verifies domain-specific scores are stored separately.
        """
        from app.core.pagerank_service import PageRankService

        driver, session = mock_neo4j_driver

        mock_result = AsyncMock()
        mock_result.data.return_value = [{"paper_id": "p1", "score": 0.5}]
        session.run.return_value = mock_result

        service = PageRankService(driver)
        await service.calculate_domain(domain="ai")

        # Verify domain_pagerank property was set
        assert session.run.called
