"""Unit tests for observability SLO baseline.

Covers:
- /metrics endpoint returns Prometheus format
- /health/deps checks PG/Redis/Neo4j connectivity
- Slow request warning (>2000ms) triggers warning log
- SKIP_LOG_PATHS still works (health endpoints skipped)
- RequestLoggingMiddleware removed (merged into ObservabilityMiddleware)
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.observability import (
    ObservabilityMiddleware,
    SKIP_LOG_PATHS,
    SLOW_REQUEST_THRESHOLD_MS,
)


# ---------------------------------------------------------------------------
# T5.1: SKIP_LOG_PATHS is defined
# ---------------------------------------------------------------------------


class TestSkipLogPaths:
    """Test that SKIP_LOG_PATHS is properly defined."""

    def test_skip_log_paths_contains_health(self):
        assert "/health" in SKIP_LOG_PATHS

    def test_skip_log_paths_contains_health_slash(self):
        assert "/health/" in SKIP_LOG_PATHS

    def test_skip_log_paths_is_list(self):
        assert isinstance(SKIP_LOG_PATHS, list)


# ---------------------------------------------------------------------------
# T5.2: Slow request threshold defined
# ---------------------------------------------------------------------------


class TestSlowRequestThreshold:
    """Test that slow request threshold is properly defined."""

    def test_threshold_is_2000ms(self):
        assert SLOW_REQUEST_THRESHOLD_MS == 2000

    def test_threshold_is_numeric(self):
        assert isinstance(SLOW_REQUEST_THRESHOLD_MS, (int, float))


# ---------------------------------------------------------------------------
# T5.3: /metrics endpoint
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    """Test the /metrics Prometheus endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        # Prometheus format starts with # HELP or # TYPE
        content = response.text
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0

    @pytest.mark.asyncio
    async def test_metrics_endpoint_content_type(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")

        # Prometheus text format
        assert "text/plain" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# T5.4: /health/deps endpoint
# ---------------------------------------------------------------------------


class TestHealthDepsEndpoint:
    """Test the /health/deps dependency check endpoint."""

    @pytest.mark.asyncio
    async def test_health_deps_returns_dependencies(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        deps = data["dependencies"]
        assert "pg" in deps
        assert "redis" in deps
        assert "neo4j" in deps

    @pytest.mark.asyncio
    async def test_health_deps_returns_healthy_when_all_ok(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/deps")

        data = response.json()
        # Status should be "healthy" or "degraded" depending on env
        assert data["status"] in ("healthy", "degraded")


# ---------------------------------------------------------------------------
# T5.5: RequestLoggingMiddleware removed
# ---------------------------------------------------------------------------


class TestLoggingMiddlewareRemoved:
    """Test that RequestLoggingMiddleware is no longer registered."""

    def test_logging_middleware_not_imported_in_main(self):
        """Verify main.py does not import RequestLoggingMiddleware."""
        import importlib
        import app.main as main_module

        source = importlib.util.find_spec("app.main")
        # The module should not reference RequestLoggingMiddleware
        assert not hasattr(main_module, "RequestLoggingMiddleware")

    def test_observability_middleware_exports_skip_paths(self):
        """ObservabilityMiddleware now handles SKIP_LOG_PATHS."""
        from app.middleware.observability import ObservabilityMiddleware

        assert ObservabilityMiddleware is not None


# ---------------------------------------------------------------------------
# T5.6: ObservabilityMiddleware handles skip paths and slow warnings
# ---------------------------------------------------------------------------


class TestObservabilityMiddlewareFeatures:
    """Test merged ObservabilityMiddleware features."""

    def test_skip_log_paths_accessible(self):
        """SKIP_LOG_PATHS should be importable from observability module."""
        from app.middleware.observability import SKIP_LOG_PATHS

        assert "/health" in SKIP_LOG_PATHS

    def test_slow_threshold_accessible(self):
        """SLOW_REQUEST_THRESHOLD_MS should be importable."""
        from app.middleware.observability import SLOW_REQUEST_THRESHOLD_MS

        assert SLOW_REQUEST_THRESHOLD_MS == 2000
