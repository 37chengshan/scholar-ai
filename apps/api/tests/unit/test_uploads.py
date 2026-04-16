"""Unit tests for uploads API routes.

Tests cover:
- Single file upload
- Batch upload creation and progress
- Upload history management
- File validation
"""

import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.uploads import router, MAX_FILE_SIZE, MAX_BATCH_FILES
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
def valid_pdf_content():
    """Create valid PDF content with magic bytes."""
    return b"%PDF-1.4\n%Test PDF content\n%%EOF"


@pytest.fixture
def invalid_content():
    """Create invalid file content (not PDF)."""
    return b"This is not a PDF file"


@pytest.fixture
def app_with_uploads():
    """Create FastAPI app with uploads router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest_asyncio.fixture
async def authenticated_client(app_with_uploads, test_user, mock_postgres_db):
    """Create authenticated async client for testing."""
    from app.deps import get_current_user, postgres_db

    # Override dependencies
    app_with_uploads.dependency_overrides[get_current_user] = lambda: test_user
    app_with_uploads.dependency_overrides[postgres_db] = mock_postgres_db

    # Also patch the module-level import
    with patch('app.api.uploads.postgres_db', mock_postgres_db):
        transport = ASGITransport(app=app_with_uploads)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app_with_uploads.dependency_overrides.clear()


# =============================================================================
# Test Cases
# =============================================================================

class TestSingleUpload:
    """Tests for POST /api/v1/uploads endpoint."""

    @pytest.mark.asyncio
    async def test_upload_pdf_creates_paper(self, authenticated_client, mock_postgres_db, test_user, valid_pdf_content):
        """Test uploading a valid PDF creates paper."""
        # Mock no existing paper
        mock_postgres_db.fetchrow.return_value = None

        # Create file upload
        files = {"file": ("test.pdf", BytesIO(valid_pdf_content), "application/pdf")}

        with patch('os.makedirs'), \
             patch('aiofiles.open', new_callable=MagicMock):
            response = await authenticated_client.post(
                "/api/v1/uploads",
                files=files
            )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "paperId" in data["data"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_returns_400(self, authenticated_client, mock_postgres_db, invalid_content):
        """Test uploading non-PDF file returns 400."""
        files = {"file": ("test.txt", BytesIO(invalid_content), "text/plain")}

        response = await authenticated_client.post(
            "/api/v1/uploads",
            files=files
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_oversized_file_returns_413(self, authenticated_client, mock_postgres_db):
        """Test uploading oversized file returns 413."""
        # Create content larger than max
        large_content = b"%PDF-1.4\n" + b"x" * (MAX_FILE_SIZE + 1)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}

        response = await authenticated_client.post(
            "/api/v1/uploads",
            files=files
        )

        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_upload_without_file_returns_400(self, authenticated_client, mock_postgres_db):
        """Test uploading without file returns 400."""
        response = await authenticated_client.post("/api/v1/uploads")

        assert response.status_code == 422  # Validation error from FastAPI


class TestBatchUpload:
    """Tests for batch upload endpoints."""

    @pytest.mark.asyncio
    async def test_create_batch_returns_batch_id(self, authenticated_client, mock_postgres_db, test_user):
        """Test creating a batch upload session."""
        files = [
            {"filename": "paper1.pdf", "fileSize": 1000},
            {"filename": "paper2.pdf", "fileSize": 2000},
        ]

        response = await authenticated_client.post(
            "/api/v1/uploads/batch",
            json={"files": files}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "batchId" in data["data"]
        assert data["data"]["totalFiles"] == 2

    @pytest.mark.asyncio
    async def test_create_batch_rejects_oversized_batch(self, authenticated_client, mock_postgres_db):
        """Test creating batch with too many files returns 400."""
        files = [
            {"filename": f"paper{i}.pdf", "fileSize": 1000}
            for i in range(MAX_BATCH_FILES + 1)
        ]

        response = await authenticated_client.post(
            "/api/v1/uploads/batch",
            json={"files": files}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_batch_rejects_empty_files(self, authenticated_client, mock_postgres_db):
        """Test creating batch with empty files array returns 400."""
        response = await authenticated_client.post(
            "/api/v1/uploads/batch",
            json={"files": []}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_batch_progress(self, authenticated_client, mock_postgres_db, test_user):
        """Test getting batch progress."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "batch-123",
            "user_id": test_user.id,
            "total_files": 3,
            "uploaded_count": 1,
            "status": "uploading",
        }
        mock_postgres_db.fetch.return_value = []

        response = await authenticated_client.get("/api/v1/uploads/batch/batch-123/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "overallProgress" in data["data"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_batch_returns_404(self, authenticated_client, mock_postgres_db):
        """Test getting non-existent batch returns 404."""
        mock_postgres_db.fetchrow.return_value = None

        response = await authenticated_client.get("/api/v1/uploads/batch/nonexistent")

        assert response.status_code == 404


class TestUploadHistory:
    """Tests for upload history endpoints."""

    @pytest.mark.asyncio
    async def test_get_upload_history(self, authenticated_client, mock_postgres_db, test_user):
        """Test getting upload history."""
        mock_records = [
            {
                "id": "history-1",
                "user_id": test_user.id,
                "filename": "test.pdf",
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc),
            }
        ]
        mock_postgres_db.fetch.return_value = mock_records
        mock_postgres_db.fetchrow.return_value = {"count": 1}

        response = await authenticated_client.get("/api/v1/uploads/history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "records" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_record_external_upload(self, authenticated_client, mock_postgres_db, test_user):
        """Test recording external URL upload."""
        response = await authenticated_client.post(
            "/api/v1/uploads/history",
            json={
                "url": "https://arxiv.org/pdf/1234.5678",
                "title": "External Paper",
                "source": "arxiv"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "uploadId" in data["data"]

    @pytest.mark.asyncio
    async def test_delete_upload_history(self, authenticated_client, mock_postgres_db, test_user):
        """Test deleting upload history record."""
        mock_postgres_db.fetchrow.return_value = {
            "id": "history-1",
            "user_id": test_user.id,
            "paper_id": None,
        }

        response = await authenticated_client.delete("/api/v1/uploads/history/history-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_history_returns_404(self, authenticated_client, mock_postgres_db):
        """Test deleting non-existent history returns 404."""
        mock_postgres_db.fetchrow.return_value = None

        response = await authenticated_client.delete("/api/v1/uploads/history/nonexistent")

        assert response.status_code == 404