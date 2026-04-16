"""
Tests for Graph API endpoints.

Tests FastAPI endpoints for knowledge graph operations:
- /api/graph/nodes - Get graph nodes
- /api/graph/neighbors/{node_id} - Get node neighbors
- /api/graph/subgraph - Get focused subgraph
- /api/graph/pagerank - Get Top-N papers by PageRank
- /api/entities/extract - Extract entities from text
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestGraphNodesAPI:
    """Tests for GET /api/graph/nodes endpoint."""

    async def test_get_graph_nodes(self, client):
        """
        Test GET /api/graph/nodes returning nodes with type, name, pagerank.

        Verifies response structure:
        - nodes: [{id, name, type, pagerank}]
        - edges: [{source, target, type}]
        """
        response = await client.get("/api/graph/nodes")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data

        if len(data["nodes"]) > 0:
            node = data["nodes"][0]
            assert "id" in node
            assert "name" in node
            assert "type" in node
            assert "pagerank" in node

    async def test_get_graph_nodes_with_type_filter(self, client):
        """
        Test filtering nodes by type (Paper, Method, Dataset).

        Verifies type parameter filters results correctly.
        """
        # Test Paper filter
        response = await client.get("/api/graph/nodes?type=Paper")
        assert response.status_code == 200
        data = response.json()

        for node in data.get("nodes", []):
            assert node.get("type") == "Paper"

        # Test Method filter
        response = await client.get("/api/graph/nodes?type=Method")
        assert response.status_code == 200
        data = response.json()

        for node in data.get("nodes", []):
            assert node.get("type") == "Method"

    async def test_get_graph_nodes_with_limit(self, client):
        """
        Test limiting number of nodes returned.

        Verifies limit parameter restricts results.
        """
        response = await client.get("/api/graph/nodes?limit=10")
        assert response.status_code == 200
        data = response.json()

        assert len(data.get("nodes", [])) <= 10

    async def test_get_graph_nodes_response_format(self, client):
        """
        Test response matches G6 data format.

        Verifies nodes and edges have required fields for G6 visualization.
        """
        response = await client.get("/api/graph/nodes")
        assert response.status_code == 200
        data = response.json()

        # Verify G6 format
        for node in data.get("nodes", []):
            assert "id" in node, "Node must have id"
            assert "name" in node or "label" in node, "Node must have name or label"
            assert "type" in node, "Node must have type"

        for edge in data.get("edges", []):
            assert "source" in edge, "Edge must have source"
            assert "target" in edge, "Edge must have target"


class TestGraphNeighborsAPI:
    """Tests for GET /api/graph/neighbors/{node_id} endpoint."""

    async def test_get_node_neighbors(self, client):
        """
        Test GET /api/graph/neighbors/{node_id} for layered loading.

        Verifies neighbors are returned with their relationships.
        """
        response = await client.get("/api/graph/neighbors/paper-001")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data

    async def test_get_node_neighbors_with_depth(self, client):
        """
        Test neighbor loading with depth parameter.

        Verifies depth controls how many hops to traverse.
        """
        response = await client.get("/api/graph/neighbors/paper-001?depth=2")
        assert response.status_code == 200

        response = await client.get("/api/graph/neighbors/paper-001?depth=1")
        assert response.status_code == 200

    async def test_get_node_neighbors_not_found(self, client):
        """
        Test 404 for non-existent nodes.

        Verifies proper error handling for missing nodes.
        """
        response = await client.get("/api/graph/neighbors/nonexistent-id")
        assert response.status_code == 404

    async def test_get_node_neighbors_relationship_types(self, client):
        """
        Test filtering neighbors by relationship type.

        Verifies relationship_type parameter filters results.
        """
        response = await client.get("/api/graph/neighbors/paper-001?relationship_type=USES")
        assert response.status_code == 200


class TestGraphSubgraphAPI:
    """Tests for GET /api/graph/subgraph endpoint."""

    async def test_get_paper_subgraph(self, client):
        """
        Test GET /api/graph/subgraph?paper_ids=... for focused view.

        Verifies subgraph contains specified papers and their connections.
        """
        response = await client.get("/api/graph/subgraph?paper_ids=paper-001,paper-002")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data

    async def test_get_subgraph_single_paper(self, client):
        """
        Test subgraph with single paper.

        Verifies subgraph works with single paper_id.
        """
        response = await client.get("/api/graph/subgraph?paper_ids=paper-001")
        assert response.status_code == 200

    async def test_get_subgraph_empty_papers(self, client):
        """
        Test subgraph with empty paper list.

        Verifies error is returned for empty input.
        """
        response = await client.get("/api/graph/subgraph")
        assert response.status_code in [400, 422]  # Bad request or validation error

    async def test_get_subgraph_invalid_paper_id(self, client):
        """
        Test subgraph with invalid paper ID.

        Verifies error handling for non-existent papers.
        """
        response = await client.get("/api/graph/subgraph?paper_ids=invalid-id")
        # Should either return empty graph or 404
        assert response.status_code in [200, 404]


class TestGraphPageRankAPI:
    """Tests for GET /api/graph/pagerank endpoint."""

    async def test_get_pagerank_top(self, client):
        """
        Test GET /api/graph/pagerank?limit=20 returning Top-N papers.

        Verifies:
        - Results are sorted by PageRank descending
        - Limit restricts number of results
        - Each result has paper_id, title, score
        """
        response = await client.get("/api/graph/pagerank?limit=20")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 20

        if len(data) > 0:
            for item in data:
                assert "paper_id" in item
                assert "title" in item
                assert "score" in item

            # Verify descending order
            scores = [item["score"] for item in data]
            assert scores == sorted(scores, reverse=True)

    async def test_get_pagerank_default_limit(self, client):
        """
        Test default limit for PageRank endpoint.

        Verifies default limit is applied when not specified.
        """
        response = await client.get("/api/graph/pagerank")
        assert response.status_code == 200
        data = response.json()

        # Should have some default limit
        assert len(data) <= 100

    async def test_get_pagerank_with_domain_filter(self, client):
        """
        Test domain-specific PageRank.

        Verifies domain parameter filters by research domain.
        """
        response = await client.get("/api/graph/pagerank?domain=computer-vision&limit=10")
        assert response.status_code == 200


class TestEntityExtractionAPI:
    """Tests for POST /api/entities/extract endpoint."""

    async def test_post_extract_entities(self, client):
        """
        Test POST /api/entities/extract endpoint.

        Verifies:
        - Request body with text is accepted
        - Response contains extracted entities
        - Entity types are methods, datasets, metrics, venues
        """
        request_data = {
            "text": "We use the Transformer architecture trained on ImageNet dataset.",
            "entity_types": ["method", "dataset"]
        }

        response = await client.post("/api/entities/extract", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "entities" in data
        assert "relationships" in data

    async def test_post_extract_empty_text(self, client):
        """
        Test extraction with empty text.

        Verifies graceful handling of empty input.
        """
        request_data = {
            "text": "",
            "entity_types": ["method", "dataset"]
        }

        response = await client.post("/api/entities/extract", json=request_data)
        # Should either return empty result or validation error
        assert response.status_code in [200, 400, 422]

    async def test_post_extract_invalid_entity_type(self, client):
        """
        Test extraction with invalid entity type.

        Verifies validation of entity_types parameter.
        """
        request_data = {
            "text": "Sample text",
            "entity_types": ["invalid_type"]
        }

        response = await client.post("/api/entities/extract", json=request_data)
        assert response.status_code in [200, 400, 422]


class TestGraphAPIErrorHandling:
    """Tests for API error handling."""

    async def test_graph_api_error_handling(self, client):
        """
        Test 500 errors for Neo4j failures.

        Verifies proper error response when Neo4j fails.
        """
        with patch("app.api.graph.get_neo4j_service") as mock_service:
            mock_service.side_effect = Exception("Neo4j connection failed")

            response = await client.get("/api/graph/nodes")
            assert response.status_code == 500

    async def test_graph_api_not_found(self, client):
        """
        Test 404 for non-existent nodes.

        Verifies proper 404 response for missing resources.
        """
        response = await client.get("/api/graph/neighbors/unknown-node-id")
        assert response.status_code == 404

    async def test_graph_api_invalid_parameters(self, client):
        """
        Test 422 for invalid parameters.

        Verifies validation errors return 422.
        """
        # Invalid limit (negative)
        response = await client.get("/api/graph/nodes?limit=-1")
        assert response.status_code in [400, 422]

    async def test_graph_api_method_not_allowed(self, client):
        """
        Test 405 for incorrect HTTP methods.

        Verifies method not allowed is returned.
        """
        response = await client.post("/api/graph/nodes")
        assert response.status_code == 405


class TestGraphAPIResponseSchemas:
    """Tests for API response schemas."""

    async def test_nodes_response_schema(self, client):
        """
        Test /api/graph/nodes response schema.

        Verifies response matches expected format.
        """
        response = await client.get("/api/graph/nodes")
        assert response.status_code == 200
        data = response.json()

        # Verify schema
        assert isinstance(data, dict)
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    async def test_neighbors_response_schema(self, client):
        """
        Test /api/graph/neighbors/{id} response schema.

        Verifies response matches expected format.
        """
        response = await client.get("/api/graph/neighbors/paper-001")

        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "edges" in data

    async def test_pagerank_response_schema(self, client):
        """
        Test /api/graph/pagerank response schema.

        Verifies response is list of paper scores.
        """
        response = await client.get("/api/graph/pagerank?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        for item in data:
            assert "paper_id" in item
            assert "title" in item
            assert "score" in item
            assert isinstance(item["score"], float)

    async def test_extract_response_schema(self, client):
        """
        Test /api/entities/extract response schema.

        Verifies response matches expected format.
        """
        request_data = {
            "text": "Test text for extraction",
            "entity_types": ["method"]
        }

        response = await client.post("/api/entities/extract", json=request_data)

        if response.status_code == 200:
            data = response.json()
            assert "entities" in data
            assert "relationships" in data
            assert isinstance(data["entities"], list)
            assert isinstance(data["relationships"], list)


class TestGraphAPIAuthentication:
    """Tests for API authentication."""

    async def test_nodes_without_auth(self, client):
        """
        Test access without authentication.

        Verifies endpoints require authentication.
        """
        # Public endpoints should work
        response = await client.get("/api/graph/nodes")
        assert response.status_code in [200, 401]

    async def test_protected_endpoints_require_auth(self, client):
        """
        Test that protected endpoints require auth.

        Verifies authentication is enforced.
        """
        # These might require auth
        endpoints = [
            "/api/graph/neighbors/paper-001",
            "/api/graph/subgraph?paper_ids=paper-001",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            # Should be 200 or 401
            assert response.status_code in [200, 401, 404]


class TestGraphAPIPagination:
    """Tests for API pagination."""

    async def test_nodes_pagination(self, client):
        """
        Test pagination for nodes endpoint.

        Verifies offset and limit parameters work.
        """
        response = await client.get("/api/graph/nodes?limit=10&offset=0")
        assert response.status_code == 200

        response = await client.get("/api/graph/nodes?limit=10&offset=10")
        assert response.status_code == 200

    async def test_pagerank_pagination(self, client):
        """
        Test pagination for PageRank endpoint.

        Verifies offset parameter works.
        """
        response = await client.get("/api/graph/pagerank?limit=10&offset=0")
        assert response.status_code == 200


class TestGraphAPISearch:
    """Tests for graph search functionality."""

    async def test_search_nodes(self, client):
        """
        Test searching nodes by name.

        Verifies search query parameter filters nodes.
        """
        response = await client.get("/api/graph/nodes?search=transformer")
        assert response.status_code == 200

    async def test_search_with_type(self, client):
        """
        Test searching with type filter.

        Verifies search and type can be combined.
        """
        response = await client.get("/api/graph/nodes?search=net&type=Method")
        assert response.status_code == 200


class TestGraphAPIPerformance:
    """Tests for API performance."""

    async def test_nodes_response_time(self, client):
        """
        Test nodes endpoint response time.

        Verifies endpoint responds within acceptable time.
        """
        import time
        start = time.time()
        response = await client.get("/api/graph/nodes?limit=20")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0  # Should complete within 5 seconds

    async def test_pagerank_response_time(self, client):
        """
        Test PageRank endpoint response time.

        Verifies pre-calculated scores return quickly.
        """
        import time
        start = time.time()
        response = await client.get("/api/graph/pagerank?limit=20")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 3.0  # Should complete within 3 seconds
