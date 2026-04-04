"""Tests for authentication dependency in Python service.

Tests the authentication pass-through from Node.js to Python service.
Node.js validates JWT and passes verified user_id via X-User-ID header.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends, HTTPException
import httpx


@pytest_asyncio.fixture
async def test_client():
    """Create an async HTTP client for testing."""
    from app.main import app as fastapi_app
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_id_from_header(self):
        """Test that dependency extracts user_id from X-User-ID header."""
        from app.utils.user_context import get_current_user_id

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test", headers={"X-User-ID": "test-user-123"})
            assert response.status_code == 200
            assert response.json()["user_id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_raises_401_when_header_missing(self):
        """Test that dependency raises 401 when X-User-ID header is missing."""
        from app.utils.user_context import get_current_user_id

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")
            assert response.status_code == 401
            assert "Unauthorized" in response.json()["detail"]["title"]

    @pytest.mark.asyncio
    async def test_raises_401_when_header_empty(self):
        """Test that dependency raises 401 when X-User-ID header is empty string."""
        from app.utils.user_context import get_current_user_id

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test", headers={"X-User-ID": ""})
            assert response.status_code == 401
            assert "Unauthorized" in response.json()["detail"]["title"]


class TestCurrentUserIdDependency:
    """Tests for CurrentUserId convenience dependency."""

    @pytest.mark.asyncio
    async def test_dependency_works_as_fastapi_depends(self):
        """Test that CurrentUserId can be used as Depends parameter."""
        from app.core.auth import CurrentUserId

        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(user_id: str = CurrentUserId):
            return {"authenticated_user": user_id}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Should work with valid header
            response = await client.get("/protected", headers={"X-User-ID": "user-abc"})
            assert response.status_code == 200
            assert response.json()["authenticated_user"] == "user-abc"

            # Should fail without header
            response = await client.get("/protected")
            assert response.status_code == 401