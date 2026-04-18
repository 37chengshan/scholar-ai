"""Health probe contract tests for basic/ready/deep endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import health


@pytest.fixture
def health_app() -> FastAPI:
    app = FastAPI()
    app.state.embedding_service = None
    app.state.reranker_service = None
    app.state.milvus_service = None
    app.state.ai_startup_mode = "lazy"
    app.include_router(health.router, prefix="/health")
    return app


@pytest.mark.asyncio
async def test_basic_probe_always_returns_alive(health_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=health_app), base_url="http://test") as client:
        response = await client.get("/health/basic")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_ready_probe_returns_profile_and_ai_status(health_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=health_app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["profile"] == "lazy"
    assert "ai_services" in data


@pytest.mark.asyncio
async def test_deep_probe_passes_when_dependencies_healthy(health_app: FastAPI):
    mocked_health = {
        "status": "healthy",
        "services": {
            "postgres": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "neo4j": {"status": "healthy"},
            "milvus": {"status": "healthy"},
        },
        "timestamp": "2026-04-18T00:00:00",
    }

    with patch("app.api.health.get_services_health", AsyncMock(return_value=mocked_health)):
        async with AsyncClient(transport=ASGITransport(app=health_app), base_url="http://test") as client:
            response = await client.get("/health/deep")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_deep_probe_returns_503_when_dependencies_degraded(health_app: FastAPI):
    mocked_health = {
        "status": "degraded",
        "services": {
            "postgres": {"status": "healthy"},
            "redis": {"status": "unhealthy", "error": "conn timeout"},
            "neo4j": {"status": "healthy"},
            "milvus": {"status": "healthy"},
        },
        "timestamp": "2026-04-18T00:00:00",
    }

    with patch("app.api.health.get_services_health", AsyncMock(return_value=mocked_health)):
        async with AsyncClient(transport=ASGITransport(app=health_app), base_url="http://test") as client:
            response = await client.get("/health/deep")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
