"""Tests for user isolation in Python API endpoints.

Ensures all endpoints properly filter data by authenticated user_id from X-User-ID header.
Users cannot access other users' data.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI
import httpx


@pytest_asyncio.fixture
async def test_app():
    """Create a FastAPI test app with session routes."""
    from app.api.session import router as session_router
    from app.api.rag import router as rag_router
    from app.api.search import router as search_router

    app = FastAPI()
    app.include_router(session_router, prefix="/api")
    app.include_router(rag_router, prefix="/api")
    app.include_router(search_router, prefix="/api")

    yield app


class TestSessionUserIsolation:
    """Tests for session endpoint user isolation."""

    @pytest.mark.asyncio
    async def test_create_session_with_authenticated_user(self, test_app):
        """Test that session creation uses authenticated user_id."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={"title": "Test Session"},
                headers={"X-User-ID": "user-123"}
            )
            assert response.status_code == 201
            data = response.json()
            assert data["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_create_session_fails_without_user_header(self, test_app):
        """Test that session creation fails without X-User-ID header."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={"title": "Test Session"}
            )
            assert response.status_code == 401
            assert "Unauthorized" in response.json()["detail"]["title"]

    @pytest.mark.asyncio
    async def test_list_sessions_filters_by_user(self, test_app):
        """Test that session list filters by authenticated user_id."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Create session for user-123
            await client.post(
                "/api/sessions",
                json={"title": "User 123 Session"},
                headers={"X-User-ID": "user-123"}
            )

            # List sessions for user-123
            response = await client.get("/api/sessions", headers={"X-User-ID": "user-123"})
            assert response.status_code == 200
            data = response.json()
            # All returned sessions should belong to user-123
            for session in data["sessions"]:
                assert session["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_session_ownership_check(self, test_app):
        """Test that getting session validates ownership."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Create session for user-123
            create_response = await client.post(
                "/api/sessions",
                json={"title": "User 123 Session"},
                headers={"X-User-ID": "user-123"}
            )
            session_id = create_response.json()["id"]

            # Try to access with different user (user-456)
            response = await client.get(
                f"/api/sessions/{session_id}",
                headers={"X-User-ID": "user-456"}
            )
            # Should return 404 (not found for this user) or 403 (forbidden)
            assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_delete_session_ownership_check(self, test_app):
        """Test that deleting session validates ownership."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Create session for user-123
            create_response = await client.post(
                "/api/sessions",
                json={"title": "User 123 Session"},
                headers={"X-User-ID": "user-123"}
            )
            session_id = create_response.json()["id"]

            # Try to delete with different user (user-456)
            response = await client.delete(
                f"/api/sessions/{session_id}",
                headers={"X-User-ID": "user-456"}
            )
            # Should return 404 (not found for this user) or 403 (forbidden)
            assert response.status_code in [403, 404]


class TestRAGUserIsolation:
    """Tests for RAG endpoint user isolation."""

    @pytest.mark.asyncio
    async def test_rag_endpoint_requires_authentication(self, test_app):
        """Test that RAG endpoints require X-User-ID header."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/rag/query",
                json={"question": "test question"}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rag_query_with_authenticated_user(self, test_app):
        """Test that RAG query uses authenticated user_id."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # This test verifies the endpoint accepts authenticated user_id
            # Actual RAG functionality requires papers in database
            response = await client.post(
                "/api/rag/query",
                json={"question": "test question"},
                headers={"X-User-ID": "user-123"}
            )
            # Endpoint should accept the request with valid authentication
            # May return 200, 404 (no papers), or other valid responses
            assert response.status_code in [200, 404, 422]


class TestSearchUserIsolation:
    """Tests for search endpoint user isolation."""

    @pytest.mark.asyncio
    async def test_library_search_requires_authentication(self, test_app):
        """Test that library search requires X-User-ID header."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/search/library?q=test")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_library_search_with_authenticated_user(self, test_app):
        """Test that library search uses authenticated user_id."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/search/library?q=test",
                headers={"X-User-ID": "user-123"}
            )
            # Endpoint should accept the request with valid authentication
            assert response.status_code in [200, 404]


class TestAuthenticationEnforcement:
    """Tests that all protected endpoints enforce authentication."""

    @pytest.mark.asyncio
    async def test_all_endpoints_require_x_user_id(self, test_app):
        """Verify all protected endpoints reject requests without X-User-ID."""
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            # Session endpoints
            endpoints_to_test = [
                ("/api/sessions", "GET"),
                ("/api/sessions", "POST"),
                ("/api/search/library", "GET"),
                ("/api/rag/query", "POST"),
            ]

            for endpoint, method in endpoints_to_test:
                if method == "GET":
                    response = await client.get(endpoint)
                elif method == "POST":
                    response = await client.post(endpoint, json={})

                # All should return 401 without authentication
                assert response.status_code == 401, f"{method} {endpoint} should require auth"