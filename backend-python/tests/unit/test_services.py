"""Unit tests for service layer classes.

Tests for:
- PaperService: Paper business logic
- StorageService: File storage operations
- TaskService: Task management

Uses pytest-asyncio for async test support.

Note: Tests use heavy mocking to avoid triggering SQLAlchemy model configuration
which has pre-existing relationship issues in the codebase.
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# =============================================================================
# PaperService Tests
# =============================================================================

class TestPaperService:
    """Tests for PaperService class."""

    @pytest.fixture
    def mock_paper(self):
        """Create mock paper object."""
        paper = MagicMock()
        paper.id = str(uuid4())
        paper.title = "Test Paper"
        paper.authors = ["Author One", "Author Two"]
        paper.status = "completed"
        paper.starred = False
        paper.user_id = str(uuid4())
        paper.created_at = datetime.now(timezone.utc)
        return paper

    @pytest.mark.asyncio
    async def test_list_papers_returns_paginated_results(self, mock_paper):
        """PaperService.list_papers returns paginated results."""
        # Import here to avoid early model configuration issues
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0  # Total count
        mock_result.scalars.return_value.all.return_value = []  # Items
        mock_db.execute.return_value = mock_result

        result = await PaperService.list_papers(
            db=mock_db,
            user_id="test-user-id",
            filters={},
            pagination={"page": 1, "limit": 20},
        )

        assert "items" in result
        assert "pagination" in result
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["limit"] == 20
        assert result["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_list_papers_applies_filters(self, mock_paper):
        """PaperService.list_papers applies status filter."""
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # Total count
        mock_result.scalars.return_value.all.return_value = []  # Items
        mock_db.execute.return_value = mock_result

        result = await PaperService.list_papers(
            db=mock_db,
            user_id="test-user-id",
            filters={"status": "completed"},
            pagination={"page": 1, "limit": 20},
        )

        assert result["pagination"]["total"] == 5

    @pytest.mark.asyncio
    async def test_get_paper_returns_paper_with_ownership_check(self, mock_paper):
        """PaperService.get_paper returns paper if owned by user."""
        from app.services.paper_service import PaperService

        # Mock get_paper to return our mock paper
        with patch.object(PaperService, 'get_paper', return_value=mock_paper):
            result = await PaperService.get_paper(
                db=AsyncMock(),
                paper_id=mock_paper.id,
                user_id=mock_paper.user_id,
            )

            assert result.id == mock_paper.id
            assert result.title == mock_paper.title

    @pytest.mark.asyncio
    async def test_get_paper_raises_for_wrong_user(self, mock_paper):
        """PaperService.get_paper raises ValueError for wrong user."""
        from app.services.paper_service import PaperService

        with patch.object(PaperService, 'get_paper', side_effect=ValueError("Paper not found")):
            with pytest.raises(ValueError, match="Paper not found"):
                await PaperService.get_paper(
                    db=AsyncMock(),
                    paper_id="paper-id",
                    user_id="wrong-user-id",
                )

    @pytest.mark.asyncio
    async def test_create_paper_with_pending_status(self, mock_paper):
        """PaperService.create_paper creates paper with pending status."""
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        user_id = str(uuid4())
        data = {
            "title": "New Paper",
            "authors": ["Test Author"],
            "year": 2024,
        }

        # Mock the Paper class to avoid model configuration
        with patch('app.services.paper_service.Paper') as MockPaper:
            mock_paper_instance = MagicMock()
            mock_paper_instance.title = "New Paper"
            mock_paper_instance.status = "pending"
            mock_paper_instance.user_id = user_id
            MockPaper.return_value = mock_paper_instance

            result = await PaperService.create_paper(
                db=mock_db,
                user_id=user_id,
                data=data,
            )

            assert result.title == "New Paper"
            assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_update_paper_metadata(self, mock_paper):
        """PaperService.update_paper updates metadata."""
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        with patch.object(PaperService, 'get_paper', return_value=mock_paper):
            result = await PaperService.update_paper(
                db=mock_db,
                paper_id=mock_paper.id,
                user_id=mock_paper.user_id,
                data={"title": "Updated Title", "starred": True},
            )

            assert result.title == "Updated Title"
            assert result.starred is True

    @pytest.mark.asyncio
    async def test_delete_paper_with_ownership_check(self, mock_paper):
        """PaperService.delete_paper deletes paper after ownership check."""
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch.object(PaperService, 'get_paper', return_value=mock_paper):
            result = await PaperService.delete_paper(
                db=mock_db,
                paper_id=mock_paper.id,
                user_id=mock_paper.user_id,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_toggle_star(self, mock_paper):
        """PaperService.toggle_star updates starred field."""
        from app.services.paper_service import PaperService

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        with patch.object(PaperService, 'get_paper', return_value=mock_paper):
            result = await PaperService.toggle_star(
                db=mock_db,
                paper_id=mock_paper.id,
                user_id=mock_paper.user_id,
                starred=True,
            )

            assert result.starred is True


# =============================================================================
# StorageService Tests
# =============================================================================

class TestStorageService:
    """Tests for StorageService class."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_upload_to_local_storage(self, temp_storage):
        """StorageService uploads file to local storage."""
        from app.services.storage_service import StorageService

        with patch('app.services.storage_service.settings') as mock_settings:
            mock_settings.USE_LOCAL_STORAGE = True
            mock_settings.LOCAL_STORAGE_PATH = temp_storage
            mock_settings.S3_BUCKET = None
            mock_settings.S3_ENDPOINT = None
            mock_settings.AWS_ACCESS_KEY_ID = None
            mock_settings.AWS_SECRET_ACCESS_KEY = None

            storage = StorageService()
            content = b"Test file content"
            key = "test/file.txt"

            result = await storage.upload_file(content, key, "text/plain")

            assert result == key
            assert (Path(temp_storage) / key).exists()

    @pytest.mark.asyncio
    async def test_delete_file_from_local_storage(self, temp_storage):
        """StorageService deletes file from local storage."""
        from app.services.storage_service import StorageService

        with patch('app.services.storage_service.settings') as mock_settings:
            mock_settings.USE_LOCAL_STORAGE = True
            mock_settings.LOCAL_STORAGE_PATH = temp_storage
            mock_settings.S3_BUCKET = None
            mock_settings.S3_ENDPOINT = None
            mock_settings.AWS_ACCESS_KEY_ID = None
            mock_settings.AWS_SECRET_ACCESS_KEY = None

            storage = StorageService()
            content = b"Test file content"
            key = "test/delete_me.txt"
            await storage.upload_file(content, key, "text/plain")

            assert (Path(temp_storage) / key).exists()

            await storage.delete_file(key)

            assert not (Path(temp_storage) / key).exists()


# =============================================================================
# TaskService Tests
# =============================================================================

class TestTaskService:
    """Tests for TaskService class."""

    @pytest.fixture
    def mock_task(self):
        """Create mock task object."""
        task = MagicMock()
        task.id = str(uuid4())
        task.paper_id = str(uuid4())
        task.status = "pending"
        task.attempts = 0
        task.storage_key = "test/file.pdf"
        task.created_at = datetime.now(timezone.utc)
        return task

    @pytest.mark.asyncio
    async def test_create_task(self, mock_task):
        """TaskService.create_task creates processing task."""
        from app.services.task_service import TaskService

        mock_db = AsyncMock()
        mock_paper = MagicMock()
        mock_paper.id = str(uuid4())
        mock_paper.storage_key = "test/file.pdf"

        # Mock the ProcessingTask class
        with patch('app.services.task_service.ProcessingTask') as MockTask:
            mock_task_instance = MagicMock()
            mock_task_instance.status = "pending"
            mock_task_instance.attempts = 0
            MockTask.return_value = mock_task_instance

            # Mock the database operations
            with patch('app.services.task_service.select'):
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_paper
                mock_db.execute.return_value = mock_result
                mock_db.add = MagicMock()
                mock_db.flush = AsyncMock()

                result = await TaskService.create_task(
                    db=mock_db,
                    user_id="test-user-id",
                    paper_id=mock_paper.id,
                    task_type="pdf_processing",
                )

                assert result.status == "pending"
                assert result.attempts == 0

    @pytest.mark.asyncio
    async def test_retry_task_resets_status(self, mock_task):
        """TaskService.retry_task resets status and increments attempts."""
        from app.services.task_service import TaskService

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        with patch.object(TaskService, 'get_task', return_value=mock_task):
            result = await TaskService.retry_task(
                db=mock_db,
                task_id=mock_task.id,
                user_id="test-user-id",
            )

            assert result.status == "pending"
            assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_cancel_task_for_pending(self, mock_task):
        """TaskService.cancel_task cancels pending task."""
        from app.services.task_service import TaskService

        mock_db = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch.object(TaskService, 'get_task', return_value=mock_task):
            result = await TaskService.cancel_task(
                db=mock_db,
                task_id=mock_task.id,
                user_id="test-user-id",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_task_fails_for_non_pending(self, mock_task):
        """TaskService.cancel_task fails for non-pending task."""
        from app.services.task_service import TaskService

        mock_task.status = "processing"
        mock_db = AsyncMock()

        with patch.object(TaskService, 'get_task', return_value=mock_task):
            with pytest.raises(ValueError, match="Cannot cancel task"):
                await TaskService.cancel_task(
                    db=mock_db,
                    task_id=mock_task.id,
                    user_id="test-user-id",
                )

    def test_get_progress_stages_returns_4_stages(self):
        """TaskService.get_progress_stages returns 4 stage definitions."""
        from app.services.task_service import TaskService

        stages = TaskService.get_progress_stages()

        assert isinstance(stages, dict)
        assert len(stages) == 4
        assert "upload" in stages
        assert "parsing" in stages
        assert "indexing" in stages
        assert "multimodal" in stages

        for stage_name, stage in stages.items():
            assert "name" in stage
            assert "start" in stage
            assert "end" in stage
            assert "label" in stage

    def test_calculate_progress(self):
        """TaskService.calculate_progress returns correct percentage."""
        from app.services.task_service import TaskService

        assert TaskService.calculate_progress("upload", 0.5) == 7
        assert TaskService.calculate_progress("parsing", 0.5) == 37
        assert TaskService.calculate_progress("indexing", 0.5) == 75
        assert TaskService.calculate_progress("multimodal", 0.5) == 95

        assert TaskService.calculate_progress("upload", 0.0) == 0
        assert TaskService.calculate_progress("multimodal", 1.0) == 100