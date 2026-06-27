"""Unit tests for papers API routes.

Tests cover:
- Paper list with pagination and filters
- Paper creation (upload URL generation)
- Paper CRUD operations
- Starred toggle
- Search functionality
"""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from types import SimpleNamespace

from app.api.papers import router
from app.services.auth_service import User
from app.services.paper_service import PaperService
from app.utils.problem_detail import ErrorTypes


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id="test-user-123",
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
        email_verified=True,
        roles=["user"],
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


def _make_paper(user_id: str, **overrides):
    now = datetime.now(timezone.utc)
    base = {
        "id": "paper-1",
        "title": "Test Paper",
        "authors": ["Author 1"],
        "year": 2024,
        "abstract": None,
        "doi": None,
        "arxiv_id": None,
        "pdf_url": None,
        "pdf_path": None,
        "content": None,
        "imrad_json": None,
        "status": "completed",
        "file_size": None,
        "page_count": None,
        "keywords": [],
        "venue": None,
        "citations": None,
        "created_at": now,
        "updated_at": now,
        "user_id": user_id,
        "storage_key": "papers/test.pdf",
        "reading_notes": None,
        "reading_card_doc": {"type": "doc", "content": []},
        "notes_version": 0,
        "starred": False,
        "project_id": None,
        "batch_id": None,
        "upload_progress": 100,
        "upload_status": "completed",
        "uploaded_at": now,
        "upload_history": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def paper_service_mocks(monkeypatch):
    mocks = SimpleNamespace(
        list_papers_for_api=AsyncMock(),
        create_paper_for_api=AsyncMock(),
        get_paper_for_api=AsyncMock(),
        update_paper_for_api=AsyncMock(),
        delete_paper_for_api=AsyncMock(),
        toggle_star=AsyncMock(),
        search_papers_for_api=AsyncMock(),
    )
    monkeypatch.setattr(PaperService, "list_papers_for_api", mocks.list_papers_for_api)
    monkeypatch.setattr(PaperService, "create_paper_for_api", mocks.create_paper_for_api)
    monkeypatch.setattr(PaperService, "get_paper_for_api", mocks.get_paper_for_api)
    monkeypatch.setattr(PaperService, "update_paper_for_api", mocks.update_paper_for_api)
    monkeypatch.setattr(PaperService, "delete_paper_for_api", mocks.delete_paper_for_api)
    monkeypatch.setattr(PaperService, "toggle_star", mocks.toggle_star)
    monkeypatch.setattr(PaperService, "search_papers_for_api", mocks.search_papers_for_api)
    return mocks


@pytest.fixture
def app_with_papers():
    """Create FastAPI app with papers router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/papers")
    return app


@pytest_asyncio.fixture
async def authenticated_client(app_with_papers, test_user, mock_db):
    """Create authenticated async client for testing."""
    from app.deps import get_current_user, get_db

    app_with_papers.dependency_overrides[get_current_user] = lambda: test_user

    async def _override_get_db():
        yield mock_db

    app_with_papers.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app_with_papers)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    app_with_papers.dependency_overrides.clear()


# =============================================================================
# Test Cases
# =============================================================================

class TestListPapers:
    """Tests for GET /api/v1/papers endpoint."""

    @pytest.mark.asyncio
    async def test_list_papers_returns_paginated_list(self, authenticated_client, paper_service_mocks, test_user):
        """Test that GET /api/v1/papers returns paginated list."""
        paper = _make_paper(test_user.id, title="Test Paper 1")
        paper_service_mocks.list_papers_for_api.return_value = {
            "papers": [paper],
            "task_map": {},
            "chunk_count_map": {"paper-1": 2},
            "total": 1,
            "page": 1,
            "limit": 20,
            "total_pages": 1,
        }

        response = await authenticated_client.get("/api/v1/papers")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "papers" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]

    @pytest.mark.asyncio
    async def test_list_papers_with_starred_filter(self, authenticated_client, paper_service_mocks, test_user):
        """Test that starred filter works correctly."""
        paper_service_mocks.list_papers_for_api.return_value = {
            "papers": [],
            "task_map": {},
            "chunk_count_map": {},
            "total": 0,
            "page": 1,
            "limit": 20,
            "total_pages": 0,
        }

        response = await authenticated_client.get("/api/v1/papers?starred=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_papers_with_pagination(self, authenticated_client, paper_service_mocks):
        """Test pagination parameters."""
        paper_service_mocks.list_papers_for_api.return_value = {
            "papers": [],
            "task_map": {},
            "chunk_count_map": {},
            "total": 100,
            "page": 2,
            "limit": 10,
            "total_pages": 10,
        }

        response = await authenticated_client.get("/api/v1/papers?page=2&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 2
        assert data["data"]["limit"] == 10


class TestCreatePaper:
    """Tests for POST /api/v1/papers endpoint."""

    @pytest.mark.asyncio
    async def test_create_paper_returns_upload_url(self, authenticated_client, paper_service_mocks, test_user):
        """Test that creating paper returns upload URL."""
        paper_service_mocks.create_paper_for_api.return_value = {
            "paperId": "paper-123",
            "uploadUrl": "/api/v1/papers/upload/local/test-key.pdf",
            "storageKey": "test-key.pdf",
            "expiresIn": 3600,
        }

        response = await authenticated_client.post(
            "/api/v1/papers",
            json={"filename": "test_paper.pdf"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "paperId" in data["data"]
        assert "uploadUrl" in data["data"]
        assert "storageKey" in data["data"]

    @pytest.mark.asyncio
    async def test_create_paper_rejects_non_pdf(self, authenticated_client, paper_service_mocks):
        """Test that non-PDF files are rejected."""
        response = await authenticated_client.post(
            "/api/v1/papers",
            json={"filename": "document.docx"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_create_paper_detects_duplicate(self, authenticated_client, paper_service_mocks, test_user):
        """Test that duplicate papers are detected."""
        paper_service_mocks.create_paper_for_api.side_effect = ValueError(
            "Duplicate paper title: test_paper"
        )

        response = await authenticated_client.post(
            "/api/v1/papers",
            json={"filename": "test_paper.pdf"}
        )

        assert response.status_code == 409
        data = response.json()
        assert "error" in data or "detail" in data


class TestGetPaper:
    """Tests for GET /api/v1/papers/:id endpoint."""

    @pytest.mark.asyncio
    async def test_get_paper_returns_details(self, authenticated_client, paper_service_mocks, test_user):
        """Test getting paper details."""
        mock_paper = _make_paper(test_user.id, id="paper-123", title="Test Paper")
        mock_task = SimpleNamespace(status="completed", error_message=None)
        paper_service_mocks.get_paper_for_api.return_value = {
            "paper": mock_paper,
            "task": mock_task,
            "chunk_count": 2,
            "chunks": [],
        }

        response = await authenticated_client.get("/api/v1/papers/paper-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "paper-123"

    @pytest.mark.asyncio
    async def test_get_paper_not_owned_returns_404(self, authenticated_client, paper_service_mocks):
        """Test that accessing another user's paper returns 404."""
        paper_service_mocks.get_paper_for_api.side_effect = ValueError("Paper not found")

        response = await authenticated_client.get("/api/v1/papers/other-user-paper")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paper_for_api_preserves_chunk_count_without_loading_chunks(
        self,
        monkeypatch,
        test_user,
    ):
        """Detail hydration must keep ready papers compare-ready even with reading_card_doc present."""

        paper = SimpleNamespace(
            id="paper-ready",
            user_id=test_user.id,
            title="LIMA: Less Is More for Alignment (v6)",
            reading_card_doc={"type": "doc", "content": []},
        )
        task = SimpleNamespace(status="completed")
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(
            scalar_one_or_none=lambda: task,
        )

        list_chunks = AsyncMock(return_value=[])
        count_chunks = AsyncMock(return_value=105)

        monkeypatch.setattr(PaperService, "__module__", PaperService.__module__)
        monkeypatch.setattr(
            "app.services.paper_service.PaperRepository.get_user_paper",
            AsyncMock(return_value=paper),
        )
        monkeypatch.setattr(
            "app.services.paper_service.PaperRepository.list_chunks",
            list_chunks,
        )
        monkeypatch.setattr(
            "app.services.paper_service.PaperRepository.count_chunks",
            count_chunks,
        )

        result = await PaperService.get_paper_for_api(
            db,
            test_user.id,
            paper_id=paper.id,
            include_chunks=False,
        )

        assert result["paper"] is paper
        assert result["task"] is task
        assert result["chunk_count"] == 105
        assert result["chunks"] == []
        list_chunks.assert_not_awaited()
        count_chunks.assert_awaited_once_with(db, paper.id)


class TestUpdatePaper:
    """Tests for PATCH /api/v1/papers/:id endpoint."""

    @pytest.mark.asyncio
    async def test_update_paper_metadata(self, authenticated_client, paper_service_mocks, test_user):
        """Test updating paper metadata."""
        paper_service_mocks.update_paper_for_api.return_value = _make_paper(
            test_user.id,
            id="paper-123",
            title="Updated Title",
            authors=["New Author"],
        )

        response = await authenticated_client.patch(
            "/api/v1/papers/paper-123",
            json={"title": "Updated Title", "authors": ["New Author"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_paper_returns_404(self, authenticated_client, paper_service_mocks):
        """Test updating non-existent paper returns 404."""
        paper_service_mocks.update_paper_for_api.side_effect = ValueError("Paper not found")

        response = await authenticated_client.patch(
            "/api/v1/papers/nonexistent",
            json={"title": "New Title"}
        )

        assert response.status_code == 404


class TestDeletePaper:
    """Tests for DELETE /api/v1/papers/:id endpoint."""

    @pytest.mark.asyncio
    async def test_delete_paper_succeeds(self, authenticated_client, paper_service_mocks, test_user):
        """Test deleting a paper."""
        paper_service_mocks.delete_paper_for_api.return_value = None
        response = await authenticated_client.delete("/api/v1/papers/paper-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_paper_returns_404(self, authenticated_client, paper_service_mocks):
        """Test deleting non-existent paper returns 404."""
        paper_service_mocks.delete_paper_for_api.side_effect = ValueError("Paper not found")

        response = await authenticated_client.delete("/api/v1/papers/nonexistent")

        assert response.status_code == 404


class TestToggleStar:
    """Tests for PATCH /api/v1/papers/:id/starred endpoint."""

    @pytest.mark.asyncio
    async def test_toggle_star_to_true(self, authenticated_client, paper_service_mocks, test_user):
        """Test starring a paper."""
        paper_service_mocks.toggle_star.return_value = _make_paper(
            test_user.id,
            id="paper-123",
            title="Test",
            starred=True,
        )

        response = await authenticated_client.patch(
            "/api/v1/papers/paper-123/starred",
            json={"starred": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_toggle_star_nonexistent_paper_returns_404(self, authenticated_client, paper_service_mocks):
        """Test starring non-existent paper returns 404."""
        paper_service_mocks.toggle_star.side_effect = ValueError("Paper not found")

        response = await authenticated_client.patch(
            "/api/v1/papers/nonexistent/starred",
            json={"starred": True}
        )

        assert response.status_code == 404


class TestSearchPapers:
    """Tests for GET /api/v1/papers/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_papers_returns_results(self, authenticated_client, paper_service_mocks, test_user):
        """Test search returns matching papers."""
        paper = _make_paper(test_user.id, title="Machine Learning Paper")
        paper_service_mocks.search_papers_for_api.return_value = {
            "papers": [paper],
            "task_map": {},
            "chunk_count_map": {"paper-1": 2},
            "total": 1,
            "page": 1,
            "limit": 20,
            "total_pages": 1,
            "query": "machine",
        }

        response = await authenticated_client.get("/api/v1/papers/search?q=machine")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "papers" in data["data"]
        assert "query" in data["data"]

    @pytest.mark.asyncio
    async def test_search_without_query_returns_422(self, authenticated_client, paper_service_mocks):
        """Test search without query parameter returns 422 (FastAPI validation error)."""
        response = await authenticated_client.get("/api/v1/papers/search")

        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_search_with_invalid_length_returns_400(self, authenticated_client, paper_service_mocks):
        """Test search with invalid query length returns 400."""
        # Query too long
        long_query = "a" * 101
        response = await authenticated_client.get(f"/api/v1/papers/search?q={long_query}")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_search_papers_can_return_filename_fallback_matches(
        self,
        authenticated_client,
        test_user,
        monkeypatch,
    ):
        """Search response can surface papers matched via upload filename fallback."""

        paper = SimpleNamespace(
            id="paper-1",
            title="Test Paper - Page 1",
            authors=[],
            year=None,
            abstract=None,
            doi=None,
            arxiv_id=None,
            pdf_url=None,
            pdf_path=None,
            content=None,
            imrad_json=None,
            status="completed",
            file_size=None,
            page_count=None,
            keywords=[],
            venue=None,
            citations=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id=test_user.id,
            storage_key="papers/test_5_pages.pdf",
            reading_notes=None,
            reading_card_doc=None,
            notes_version=0,
            starred=False,
            project_id=None,
            batch_id=None,
            upload_progress=100,
            upload_status="completed",
            uploaded_at=datetime.now(timezone.utc),
            upload_history=[
                SimpleNamespace(
                    filename="test_5_pages.pdf",
                    created_at=datetime.now(timezone.utc),
                )
            ],
        )

        async def mock_search(*args, **kwargs):
            return {
                "papers": [paper],
                "task_map": {},
                "chunk_count_map": {"paper-1": 2},
                "total": 1,
                "page": 1,
                "limit": 20,
                "total_pages": 1,
                "query": "test_5_pages",
            }

        monkeypatch.setattr(PaperService, "search_papers_for_api", mock_search)

        response = await authenticated_client.get("/api/v1/papers/search?q=test_5_pages")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["papers"][0]["title"] == "test_5_pages"
