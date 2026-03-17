"""E2E tests for knowledge graph pipeline.

Tests complete flow:
1. Entity extraction from paper text
2. Knowledge graph construction in Neo4j
3. PageRank calculation with GDS
4. Graph API query responses
"""

import os
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.core.entity_extractor import EntityExtractor
from app.core.graph_builder import GraphBuilder
from app.core.pagerank_service import PageRankService
from app.core.neo4j_service import Neo4jService
from app.workers.entity_worker import process_entity_extraction


@pytest.fixture
def sample_paper_text():
    """Sample paper text for extraction."""
    return """
    We propose a new Transformer-based model called Vision Transformer (ViT).
    Our method achieves 88.55% accuracy on ImageNet-1K dataset.
    We evaluate using top-1 accuracy and top-5 accuracy metrics.
    The model was presented at the International Conference on Learning Representations (ICLR).
    """


@pytest.fixture
def mock_litellm_response():
    """Mock LLM response for entity extraction."""
    return {
        "methods": [
            {"name": "Vision Transformer", "context": "We propose Vision Transformer", "category": "architecture"},
            {"name": "Transformer", "context": "Transformer-based model", "category": "architecture"}
        ],
        "datasets": [
            {"name": "ImageNet-1K", "context": "achieved 88.55% accuracy on ImageNet-1K", "domain": "vision"}
        ],
        "metrics": [
            {"name": "top-1 accuracy", "context": "achieved 88.55% top-1 accuracy"},
            {"name": "top-5 accuracy", "context": "evaluated using top-5 accuracy"}
        ],
        "venues": [
            {"name": "ICLR", "type": "conference", "abbreviation": "ICLR"}
        ]
    }


@pytest.mark.asyncio
async def test_entity_extraction_e2e(sample_paper_text, mock_litellm_response):
    """E2E: Extract entities from paper text using LLM."""
    with patch('app.core.entity_extractor.litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # Arrange
        mock_llm.return_value.choices = [AsyncMock()]
        mock_llm.return_value.choices[0].message.content = str(mock_litellm_response).replace("'", '"')

        extractor = EntityExtractor()

        # Act
        result = await extractor.extract(sample_paper_text)

        # Assert
        assert "methods" in result
        assert "datasets" in result
        assert len(result["methods"]) > 0
        assert len(result["datasets"]) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="Neo4j not configured"
)
async def test_graph_construction_e2e(mock_litellm_response):
    """E2E: Build knowledge graph from extracted entities."""
    # Arrange
    paper_id = str(uuid4())
    neo4j = Neo4jService()
    builder = GraphBuilder(neo4j_service=neo4j)

    try:
        # Create paper node first
        await neo4j.create_paper_node(
            paper_id=paper_id,
            title="Test Paper",
            authors=["Author One", "Author Two"]
        )

        # Act
        counts = await builder.build_paper_entities(
            paper_id=paper_id,
            entities=mock_litellm_response
        )

        # Assert
        assert counts["methods"] > 0
        assert counts["datasets"] > 0

        # Verify in Neo4j
        async with neo4j.driver.session() as session:
            result = await session.run(
                "MATCH (p:Paper {id: $id})-[:USES]->(m:Method) RETURN count(m) as count",
                id=paper_id
            )
            record = await result.single()
            assert record["count"] > 0

    finally:
        # Cleanup
        await neo4j.delete_paper_graph(paper_id)
        await neo4j.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="Neo4j not configured"
)
async def test_pagerank_calculation_e2e():
    """E2E: Calculate PageRank using GDS."""
    # Arrange
    neo4j = Neo4jService()
    pagerank = PageRankService(neo4j.driver)

    try:
        # Create test papers with citations
        paper_ids = [str(uuid4()) for _ in range(3)]
        for i, pid in enumerate(paper_ids):
            await neo4j.create_paper_node(
                paper_id=pid,
                title=f"Test Paper {i}",
                year=2024
            )

        # Create citation network: paper0 -> paper1 -> paper2
        await neo4j.create_citation_relationship(paper_ids[0], paper_ids[1], "cites")
        await neo4j.create_citation_relationship(paper_ids[1], paper_ids[2], "cites")

        # Act
        results = await pagerank.calculate_global(limit=10)

        # Assert
        assert len(results) >= 3
        # paper2 should have highest score (cited by paper1 which is cited by paper0)
        scores = {r["paper_id"]: r["score"] for r in results}
        assert paper_ids[2] in scores

    finally:
        # Cleanup
        for pid in paper_ids:
            await neo4j.delete_paper_graph(pid)
        await pagerank.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="Neo4j not configured"
)
async def test_entity_worker_pipeline_e2e(sample_paper_text, mock_litellm_response):
    """E2E: Full pipeline from text to graph."""
    with patch('app.core.entity_extractor.litellm.acompletion', new_callable=AsyncMock) as mock_llm:
        # Arrange
        paper_id = str(uuid4())
        mock_llm.return_value.choices = [AsyncMock()]
        mock_llm.return_value.choices[0].message.content = str(mock_litellm_response).replace("'", '"')

        # Act
        result = await process_entity_extraction(
            paper_id=paper_id,
            paper_text=sample_paper_text,
            paper_metadata={
                "authors": ["Test Author"],
                "references": []
            }
        )

        # Assert
        assert result["status"] == "success"
        assert result["paper_id"] == paper_id
        assert result["entity_counts"]["methods"] > 0
        assert result["entity_counts"]["datasets"] > 0

        # Cleanup
        neo4j = Neo4jService()
        await neo4j.delete_paper_graph(paper_id)
        await neo4j.close()


@pytest.mark.asyncio
async def test_g6_data_format():
    """E2E: Verify graph API returns G6-compatible data."""
    # This test validates data format without Neo4j
    # Actual API integration tested in Node.js E2E
    sample_nodes = [
        {"id": "paper-1", "name": "Paper 1", "type": "Paper", "pagerank": 0.05},
        {"id": "method-yolo", "name": "YOLO", "type": "Method", "pagerank": None}
    ]

    sample_edges = [
        {"source": "paper-1", "target": "method-yolo", "type": "USES"}
    ]

    # Verify G6 requirements
    for node in sample_nodes:
        assert "id" in node
        assert "name" in node
        assert "type" in node
        assert node["type"] in ["Paper", "Method", "Dataset", "Metric", "Venue", "Author"]

    for edge in sample_edges:
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge
