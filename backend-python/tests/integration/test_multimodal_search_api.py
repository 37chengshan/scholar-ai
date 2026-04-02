"""Integration tests for multimodal search API endpoint.

Tests for POST /api/search/multimodal endpoint.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.main import app


class TestMultimodalSearchAPI:
    """Integration tests for multimodal search endpoint."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks for each test."""
        # Mock multimodal search service
        self.mock_search_service = Mock()
        self.mock_search_service.search = AsyncMock(
            return_value={
                "query": "test query",
                "intent": "default",
                "weights": {"text": 0.5, "image": 0.3, "table": 0.2},
                "results": [
                    {
                        "id": "result-1",
                        "paper_id": "paper-1",
                        "page_num": 1,
                        "content_data": "Test result content",
                        "score": 0.9,
                    }
                ],
                "total_count": 1,
            }
        )

        # Mock page clustering
        self.mock_clusters = {
            0: [
                {
                    "id": "result-1",
                    "paper_id": "paper-1",
                    "page_num": 1,
                    "content_data": "Test result",
                }
            ]
        }

        with patch(
            "app.api.search.get_multimodal_search_service",
            return_value=self.mock_search_service,
        ), patch(
            "app.api.search.cluster_pages",
            return_value=self.mock_clusters,
        ):
            yield

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_basic(self):
        """Test basic POST request returns results."""
        request_data = {
            "query": "YOLO architecture",
            "paper_ids": ["paper-1", "paper-2"],
            "top_k": 10,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/search/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "intent" in data
        assert "results" in data
        assert data["query"] == "test query"
        assert data["intent"] == "default"
        assert len(data["results"]) >= 1

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_clustering(self):
        """Test that response includes clusters when enabled."""
        request_data = {
            "query": "neural network diagram",
            "paper_ids": ["paper-1"],
            "top_k": 10,
            "enable_clustering": True,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/search/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert data["clusters"] is not None
        assert len(data["clusters"]) >= 1
        cluster = data["clusters"][0]
        assert "cluster_id" in cluster
        assert "pages" in cluster
        assert "results" in cluster

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_intent_detection(self):
        """Test that query with 'figure' returns image_weighted intent."""
        self.mock_search_service.search = AsyncMock(
            return_value={
                "query": "YOLO figure architecture",
                "intent": "image_weighted",
                "weights": {"text": 0.3, "image": 0.6, "table": 0.1},
                "results": [
                    {
                        "id": "img-1",
                        "paper_id": "paper-1",
                        "page_num": 5,
                        "content_data": "Figure: YOLO architecture diagram",
                        "content_type": "image",
                    }
                ],
                "total_count": 1,
            }
        )

        request_data = {
            "query": "YOLO figure architecture",
            "paper_ids": ["paper-1"],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/search/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "image_weighted"
        assert data["weights"]["image"] == 0.6

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_without_clustering(self):
        """Test that clustering can be disabled."""
        request_data = {
            "query": "machine learning",
            "paper_ids": ["paper-1"],
            "enable_clustering": False,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/search/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data.get("clusters") is None

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_validation_error(self):
        """Test validation error for missing required fields."""
        request_data = {
            "query": "test query",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/search/multimodal", json=request_data)

        assert response.status_code == 422  # Validation error