"""PageRank calculation service using Neo4j Graph Data Science library.

Provides:
- Global PageRank calculation for paper citation network
- Domain-specific PageRank for subgraph analysis
- Top-N paper retrieval with filtering
"""

from typing import Dict, List, Optional, Any
from neo4j import AsyncDriver
from app.utils.logger import logger


class PageRankService:
    """Calculate PageRank using Neo4j Graph Data Science library."""

    def __init__(self, driver: Optional[AsyncDriver] = None):
        """Initialize with Neo4j driver."""
        self.driver = driver
        self._graph_name = "paper-citations"
        self.graph_name = self._graph_name  # Public alias for test compatibility
        self._default_config = {
            "dampingFactor": 0.9,
            "maxIterations": 20,
            "tolerance": 0.0001
        }

    def _get_driver(self) -> AsyncDriver:
        """Get Neo4j driver, initializing if needed."""
        if self.driver is None:
            from app.core.neo4j_service import Neo4jService
            neo4j = Neo4jService()
            self.driver = neo4j.driver
        return self.driver

    async def _ensure_graph_projection(self) -> bool:
        """Ensure GDS graph projection exists for paper citation network.

        Returns:
            True if projection created or already exists
        """
        driver = self._get_driver()
        async with driver.session() as session:
            # Check if projection exists
            result = await session.run(
                "CALL gds.graph.exists($graph_name) YIELD exists",
                graph_name=self._graph_name
            )
            record = await result.single()
            exists = record["exists"] if record else False

            if not exists:
                logger.info("Creating GDS graph projection", graph=self._graph_name)
                try:
                    await session.run("""
                        CALL gds.graph.project(
                            $graph_name,
                            'Paper',
                            'CITES'
                        )
                    """, graph_name=self._graph_name)
                    logger.info("GDS graph projection created")
                    return True
                except Exception as e:
                    logger.error("Failed to create graph projection", error=str(e))
                    return False
            return True

    async def calculate_global(
        self,
        limit: int = 100,
        damping_factor: Optional[float] = None,
        max_iterations: Optional[int] = None,
        tolerance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Calculate global PageRank for all papers.

        Args:
            limit: Maximum number of results to return
            damping_factor: PageRank damping factor (default: 0.9)
            max_iterations: Maximum iterations (default: 20)
            tolerance: Convergence tolerance (default: 0.0001)

        Returns:
            List of dicts with paper_id, title, year, score
        """
        driver = self._get_driver()

        # Ensure projection exists
        if not await self._ensure_graph_projection():
            logger.error("Cannot calculate PageRank: graph projection failed")
            return []

        # Use provided parameters or defaults
        damping = damping_factor or self._default_config["dampingFactor"]
        max_iter = max_iterations or self._default_config["maxIterations"]
        tol = tolerance or self._default_config["tolerance"]

        async with driver.session() as session:
            try:
                result = await session.run("""
                    CALL gds.pageRank.stream($graph_name, {
                        dampingFactor: $damping,
                        maxIterations: $max_iter,
                        tolerance: $tolerance
                    })
                    YIELD nodeId, score
                    MATCH (p:Paper) WHERE id(p) = nodeId
                    SET p.global_pagerank = score
                    RETURN p.id as paper_id,
                           p.title as title,
                           p.year as year,
                           score
                    ORDER BY score DESC
                    LIMIT $limit
                """,
                    graph_name=self._graph_name,
                    damping=damping,
                    max_iter=max_iter,
                    tolerance=tol,
                    limit=limit
                )

                records = await result.data()
                logger.info("PageRank calculation complete",
                           results=len(records), limit=limit)
                return records

            except Exception as e:
                logger.error("PageRank calculation failed", error=str(e))
                return []

    async def calculate_domain(
        self,
        domain: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Calculate domain-specific PageRank for papers in a research domain.

        Args:
            domain: Research domain to filter papers
            limit: Maximum number of results to return

        Returns:
            List of paper dicts with domain-specific PageRank scores
        """
        driver = self._get_driver()

        async with driver.session() as session:
            try:
                # Create domain-specific subgraph projection
                domain_graph_name = f"paper-citations-{domain.replace(' ', '-').lower()}"

                # Check if domain projection exists
                result = await session.run(
                    "CALL gds.graph.exists($graph_name) YIELD exists",
                    graph_name=domain_graph_name
                )
                record = await result.single()
                exists = record["exists"] if record else False

                if not exists:
                    # Create domain-specific projection
                    await session.run("""
                        CALL gds.graph.project(
                            $graph_name,
                            {
                                Paper: {
                                    properties: ['id', 'title', 'year', 'domain']
                                }
                            },
                            {
                                CITES: {
                                    orientation: 'NATURAL'
                                }
                            }
                        )
                        YIELD graphName
                    """, graph_name=domain_graph_name)

                # Calculate PageRank on domain subgraph
                result = await session.run("""
                    CALL gds.pageRank.stream($graph_name, {
                        dampingFactor: $damping,
                        maxIterations: $max_iter,
                        tolerance: $tolerance
                    })
                    YIELD nodeId, score
                    MATCH (p:Paper) WHERE id(p) = nodeId
                    SET p.domain_pagerank = score
                    RETURN p.id as paper_id,
                           p.title as title,
                           p.year as year,
                           score
                    ORDER BY score DESC
                    LIMIT $limit
                """,
                    graph_name=domain_graph_name,
                    damping=self._default_config["dampingFactor"],
                    max_iter=self._default_config["maxIterations"],
                    tolerance=self._default_config["tolerance"],
                    limit=limit
                )

                records = await result.data()
                logger.info("Domain PageRank calculation complete",
                           domain=domain, results=len(records))
                return records

            except Exception as e:
                logger.error("Domain PageRank calculation failed",
                           domain=domain, error=str(e))
                return []

    async def get_top_papers(
        self,
        limit: int = 20,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get top papers by PageRank with optional year filtering.

        Args:
            limit: Number of papers to return
            min_year: Optional minimum year filter
            max_year: Optional maximum year filter

        Returns:
            List of paper dicts with pagerank score
        """
        driver = self._get_driver()

        async with driver.session() as session:
            # Build query with optional year filters
            where_clause = ""
            params: Dict[str, Any] = {"limit": limit}

            if min_year is not None:
                where_clause += " AND p.year >= $min_year"
                params["min_year"] = min_year
            if max_year is not None:
                where_clause += " AND p.year <= $max_year"
                params["max_year"] = max_year

            query = f"""
                MATCH (p:Paper)
                WHERE p.global_pagerank IS NOT NULL{where_clause}
                RETURN p.id as paper_id,
                       p.title as title,
                       p.year as year,
                       p.global_pagerank as pagerank
                ORDER BY p.global_pagerank DESC
                LIMIT $limit
            """

            result = await session.run(query, **params)
            return await result.data()

    async def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
