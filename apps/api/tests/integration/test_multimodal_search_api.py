"""Integration tests for the canonical multimodal search API."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.auth import get_current_user_id


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    yield
    app.dependency_overrides.clear()


class TestMultimodalSearchAPI:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
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

        with (
            patch(
                "app.api.search.get_multimodal_search_service",
                return_value=self.mock_search_service,
            ),
            patch(
                "app.api.search.multimodal.get_multimodal_search_service",
                return_value=self.mock_search_service,
            ),
            patch(
                "app.api.search.multimodal.cluster_pages",
                new=AsyncMock(return_value=self.mock_clusters),
            ),
        ):
            yield

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_basic(self):
        request_data = {
            "query": "YOLO architecture",
            "paper_ids": ["paper-1", "paper-2"],
            "top_k": 10,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.post("/api/v1/search/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["query"] == "test query"
        assert data["intent"] == "default"
        assert len(data["results"]) == 1
        assert data["totalCount"] == 1

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_clustering(self):
        request_data = {
            "query": "neural network diagram",
            "paper_ids": ["paper-1"],
            "top_k": 10,
            "enable_clustering": True,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.post("/api/v1/search/multimodal", json=request_data)

        assert response.status_code == 200
        clusters = response.json()["data"]["clusters"]
        assert clusters is not None
        assert len(clusters) == 1
        assert clusters[0]["clusterId"] == 0
        assert clusters[0]["pages"] == [1]
        assert len(clusters[0]["results"]) == 1

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_intent_detection(self):
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

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/v1/search/multimodal",
                json={"query": "YOLO figure architecture", "paper_ids": ["paper-1"]},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["intent"] == "image_weighted"
        assert data["weights"]["image"] == 0.6

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_without_clustering(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/v1/search/multimodal",
                json={
                    "query": "machine learning",
                    "paper_ids": ["paper-1"],
                    "enable_clustering": False,
                },
            )

        assert response.status_code == 200
        assert response.json()["data"]["clusters"] is None

    @pytest.mark.asyncio
    async def test_multimodal_endpoint_validation_error(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/v1/search/multimodal",
                json={"query": "test query"},
            )

        assert response.status_code == 400
