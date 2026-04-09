"""Unit tests for tasks API routes.

Tests cover:
- Task listing with filters
- Task detail retrieval
- Task retry
- Task progress with stages
- Task cancellation
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.tasks import router
from app.services.auth_service import User


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
def mock_postgres_db():
    """Mock database for testing."""
    mock = AsyncMock()
    mock.fetch = AsyncMock(return_value=[])
    mock.fetchrow = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_task():
    """Create a mock task."""
    return {
        "id": "task-123",
        "paper_id": "paper-456",
        "status": "completed",
        "storage_key": "test/path.pdf",
        "error_message": None,
        "attempts": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def app_with_tasks():
    """Create FastAPI app with tasks router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest_asyncio.fixture
async def authenticated_client(app_with_tasks, test_user, mock_postgres_db):
    """Create authenticated async client for testing."""
    from app.deps import get_current_user, postgres_db

    # Override dependencies
    app_with_tasks.dependency_overrides[get_current_user] = lambda: test_user
    app_with_tasks.dependency_overrides[postgres_db] = mock_postgres_db

    # Also patch the module-level import
    with patch('app.api.tasks.postgres_db', mock_postgres_db):
        transport = ASGITransport(app=app_with_tasks)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app_with_tasks.dependency_overrides.clear()


# =============================================================================
# Test Cases
# =============================================================================

class TestListTasks:
    """Tests for GET /api/v1/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_returns_user_tasks(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test listing tasks for user's papers."""
        mock_tasks = [mock_task]
        mock_tasks[0]["paper_title"] = "Test Paper"
        mock_postgres_db.fetch.return_value = mock_tasks
        mock_postgres_db.fetchrow.return_value = {"count": 1}

        response = await authenticated_client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tasks" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_list_tasks_with_paper_filter(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test listing tasks filtered by paper ID."""
        mock_task["paper_title"] = "Test Paper"
        mock_postgres_db.fetch.return_value = [mock_task]
        mock_postgres_db.fetchrow.return_value = {"count": 1}

        response = await authenticated_client.get("/api/v1/tasks?paperId=paper-456")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test listing tasks filtered by status."""
        mock_task["paper_title"] = "Test Paper"
        mock_postgres_db.fetch.return_value = [mock_task]
        mock_postgres_db.fetchrow.return_value = {"count": 1}

        response = await authenticated_client.get("/api/v1/tasks?status_filter=completed")

        assert response.status_code == 200


class TestGetTask:
    """Tests for GET /api/v1/tasks/:id endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_returns_details(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test getting task details."""
        mock_task["paper_title"] = "Test Paper"
        mock_task["user_id"] = test_user.id
        mock_postgres_db.fetchrow.return_value = mock_task

        response = await authenticated_client.get("/api/v1/tasks/task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "task-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_returns_404(self, authenticated_client, mock_postgres_db):
        """Test getting non-existent task returns 404."""
        mock_postgres_db.fetchrow.return_value = None

        response = await authenticated_client.get("/api/v1/tasks/nonexistent")

        assert response.status_code == 404


class TestRetryTask:
    """Tests for POST /api/v1/tasks/:id/retry endpoint."""

    @pytest.mark.asyncio
    async def test_retry_failed_task(self, authenticated_client, mock_postgres_db, test_user):
        """Test retrying a failed task."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "task-123",
            "status": "failed",
            "paper_id": "paper-456",
            "user_id": test_user.id,
        }

        response = await authenticated_client.post("/api/v1/tasks/task-123/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_retry_non_failed_task_returns_400(self, authenticated_client, mock_postgres_db, test_user):
        """Test retrying non-failed task returns 400."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "task-123",
            "status": "completed",
            "paper_id": "paper-456",
            "user_id": test_user.id,
        }

        response = await authenticated_client.post("/api/v1/tasks/task-123/retry")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_nonexistent_task_returns_404(self, authenticated_client, mock_postgres_db):
        """Test retrying non-existent task returns 404."""
        mock_postgres_db.fetchrow.return_value = None

        response = await authenticated_client.post("/api/v1/tasks/nonexistent/retry")

        assert response.status_code == 404


class TestTaskProgress:
    """Tests for GET /api/v1/tasks/:id/progress endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_progress_with_stages(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test getting task progress with stages."""
        mock_task["paper_title"] = "Test Paper"
        mock_task["page_count"] = 10
        mock_postgres_db.fetchrow.return_value = mock_task

        response = await authenticated_client.get("/api/v1/tasks/task-123/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stages" in data["data"]
        assert len(data["data"]["stages"]) == 4

    @pytest.mark.asyncio
    async def test_progress_stages_have_correct_structure(self, authenticated_client, mock_postgres_db, test_user, mock_task):
        """Test that progress stages have correct structure."""
        mock_task["paper_title"] = "Test Paper"
        mock_task["page_count"] = 10
        mock_postgres_db.fetchrow.return_value = mock_task

        response = await authenticated_client.get("/api/v1/tasks/task-123/progress")
        data = response.json()

        for stage in data["data"]["stages"]:
            assert "name" in stage
            assert "label" in stage
            assert "start" in stage
            assert "end" in stage
            assert "weight" in stage
            assert "completed" in stage
            assert "current" in stage

    @pytest.mark.asyncio
    async def test_completed_task_shows_all_stages_complete(self, authenticated_client, mock_postgres_db, test_user):
        """Test that completed task shows all stages as complete."""
        completed_task = {
            "id": "task-123",
            "paper_id": "paper-456",
            "status": "completed",
            "storage_key": "test/path.pdf",
            "error_message": None,
            "attempts": 1,
            "paper_title": "Test Paper",
            "page_count": 10,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
        }
        mock_postgres_db.fetchrow.return_value = completed_task

        response = await authenticated_client.get("/api/v1/tasks/task-123/progress")
        data = response.json()

        assert data["data"]["progress"] == 100
        assert data["data"]["currentStage"] == "completed"


class TestCancelTask:
    """Tests for DELETE /api/v1/tasks/:id endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, authenticated_client, mock_postgres_db, test_user):
        """Test cancelling a pending task."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "task-123",
            "status": "pending",
            "paper_id": "paper-456",
            "user_id": test_user.id,
        }

        response = await authenticated_client.delete("/api/v1/tasks/task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled" in data["data"]["message"].lower() or "success" in data["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_non_pending_task_returns_400(self, authenticated_client, mock_postgres_db, test_user):
        """Test cancelling non-pending task returns 400."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "task-123",
            "status": "processing",
            "paper_id": "paper-456",
            "user_id": test_user.id,
        }

        response = await authenticated_client.delete("/api/v1/tasks/task-123")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task_returns_404(self, authenticated_client, mock_postgres_db):
        """Test cancelling non-existent task returns 404."""
        mock_postgres_db.fetchrow.return_value = None

        response = await authenticated_client.delete("/api/v1/tasks/nonexistent")

        assert response.status_code == 404