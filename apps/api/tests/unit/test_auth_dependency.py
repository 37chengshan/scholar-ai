"""Tests for current auth dependencies in the Python service."""

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi import Depends, FastAPI


class TestGetCurrentUserId:
    @pytest.mark.asyncio
    async def test_returns_user_id_from_authenticated_user(self):
        from app.middleware.auth import get_current_user_id

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        async def fake_get_current_user(request, token=None):
            return SimpleNamespace(id="test-user-123")

        with patch("app.middleware.auth.get_current_user", side_effect=fake_get_current_user):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/test")

        assert response.status_code == 200
        assert response.json()["user_id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_raises_401_when_token_missing(self):
        from app.middleware.auth import get_current_user_id

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
    async def test_propagates_authenticated_user_lookup_failure(self):
        from app.middleware.auth import get_current_user_id

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        async def fake_get_current_user(request, token=None):
            raise Exception("lookup failed")

        with patch("app.middleware.auth.get_current_user", side_effect=fake_get_current_user):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with pytest.raises(Exception, match="lookup failed"):
                    await client.get("/test")


class TestCurrentUserIdDependency:
    @pytest.mark.asyncio
    async def test_dependency_works_as_fastapi_depends(self):
        from app.deps import CurrentUserId

        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(user_id: str = CurrentUserId):
            return {"authenticated_user": user_id}

        async def fake_get_current_user(request, token=None):
            return SimpleNamespace(id="user-abc")

        with patch("app.middleware.auth.get_current_user", side_effect=fake_get_current_user):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/protected")

        assert response.status_code == 200
        assert response.json()["authenticated_user"] == "user-abc"
