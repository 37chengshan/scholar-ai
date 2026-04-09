"""Unit tests for note tool implementations.

Tests cover:
- create_note: Create new note
- update_note: Update existing note
- ask_user_confirmation: Request user confirmation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.tools.note_tools import (
    execute_create_note,
    execute_update_note,
    execute_ask_user_confirmation,
)


@pytest.mark.asyncio
class TestCreateNoteTool:
    """Tests for create_note tool."""

    async def test_create_note_standalone(self):
        """Test creating a standalone note."""
        params = {
            "title": "My Research Notes",
            "content": "Important findings from the paper...",
            "paper_ids": [],
            "tags": ["research", "findings"]
        }

        # Create a mock Note object
        mock_note = MagicMock()
        mock_note.id = "note-123"
        mock_note.title = "My Research Notes"
        mock_note.content = "Important findings from the paper..."
        mock_note.tags = ["research", "findings"]
        mock_note.paper_ids = []
        mock_note.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_note.updated_at = datetime(2024, 1, 1, 0, 0, 0)

        # Mock the session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.tools.note_tools.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            # Patch Note constructor to return our mock
            with patch("app.tools.note_tools.Note") as mock_note_class:
                mock_note_class.return_value = mock_note

                result = await execute_create_note(params, user_id="user-123")

                assert result["success"] is True
                assert result["data"]["id"] == "note-123"
                assert result["data"]["title"] == "My Research Notes"

    async def test_create_note_linked_to_paper(self):
        """Test creating a note linked to papers."""
        params = {
            "title": "Paper Summary",
            "content": "This paper proposes a new method...",
            "paper_ids": ["paper-1", "paper-2"],
            "tags": ["summary"]
        }

        mock_note = MagicMock()
        mock_note.id = "note-456"
        mock_note.title = "Paper Summary"
        mock_note.content = "This paper proposes a new method..."
        mock_note.tags = ["summary"]
        mock_note.paper_ids = ["paper-1", "paper-2"]
        mock_note.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_note.updated_at = datetime(2024, 1, 1, 0, 0, 0)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.tools.note_tools.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch("app.tools.note_tools.Note") as mock_note_class:
                mock_note_class.return_value = mock_note

                result = await execute_create_note(params, user_id="user-123")

                assert result["success"] is True
                assert len(result["data"]["paper_ids"]) == 2

    async def test_create_note_validates_required_fields(self):
        """Test create_note validates title and content are required."""
        params = {
            "title": "",
            "content": ""
        }

        result = await execute_create_note(params, user_id="user-123")

        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
class TestUpdateNoteTool:
    """Tests for update_note tool."""

    async def test_update_note_content(self):
        """Test updating note content."""
        params = {
            "note_id": "note-123",
            "updates": {
                "content": "Updated content with new insights..."
            }
        }

        # Create a mock Note object that will be fetched and updated
        mock_note = MagicMock()
        mock_note.id = "note-123"
        mock_note.title = "Original Title"
        mock_note.content = "Updated content with new insights..."
        mock_note.tags = []
        mock_note.paper_ids = []
        mock_note.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_note.updated_at = datetime(2024, 1, 2, 0, 0, 0)

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_note)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.tools.note_tools.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await execute_update_note(params, user_id="user-123")

            assert result["success"] is True
            assert result["data"]["content"] == "Updated content with new insights..."

    async def test_update_note_tags(self):
        """Test updating note tags."""
        params = {
            "note_id": "note-123",
            "updates": {
                "tags": ["important", "review"]
            }
        }

        mock_note = MagicMock()
        mock_note.id = "note-123"
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.tags = ["important", "review"]
        mock_note.paper_ids = []
        mock_note.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_note.updated_at = datetime(2024, 1, 2, 0, 0, 0)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_note)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.tools.note_tools.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await execute_update_note(params, user_id="user-123")

            assert result["success"] is True

    async def test_update_note_validates_ownership(self):
        """Test update_note validates user owns the note."""
        params = {
            "note_id": "note-123",
            "updates": {"content": "New content"}
        }

        # Mock result that returns None (note not found or not owned)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.tools.note_tools.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await execute_update_note(params, user_id="different-user")

            assert result["success"] is False


@pytest.mark.asyncio
class TestAskUserConfirmationTool:
    """Tests for ask_user_confirmation tool."""

    async def test_ask_user_confirmation_returns_signal(self):
        """Test ask_user_confirmation returns confirmation_required signal."""
        params = {
            "message": "This will delete the paper. Continue?",
            "details": {
                "operation": "delete_paper",
                "paper_id": "paper-123"
            }
        }

        result = await execute_ask_user_confirmation(params)

        assert result["success"] is True
        assert result["data"]["confirmation_required"] is True
        assert result["data"]["message"] == "This will delete the paper. Continue?"

    async def test_ask_user_confirmation_includes_details(self):
        """Test ask_user_confirmation includes operation details."""
        params = {
            "message": "Confirm operation?",
            "details": {
                "operation": "upload_paper",
                "file_size": "50MB"
            }
        }

        result = await execute_ask_user_confirmation(params)

        assert result["success"] is True
        assert "details" in result["data"]
        assert result["data"]["details"]["operation"] == "upload_paper"