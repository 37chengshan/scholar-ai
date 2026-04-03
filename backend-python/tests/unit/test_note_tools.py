"""Unit tests for note tool implementations.

Tests cover:
- create_note: Create new note
- update_note: Update existing note
- ask_user_confirmation: Request user confirmation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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

        with patch("app.tools.note_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value="note-123")
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "note-123",
                "title": "My Research Notes",
                "content": "Important findings from the paper...",
                "tags": ["research", "findings"],
                "paper_ids": [],
                "created_at": "2024-01-01T00:00:00Z"
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

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

        with patch("app.tools.note_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "note-456",
                "title": "Paper Summary",
                "content": "This paper proposes a new method...",
                "paper_ids": ["paper-1", "paper-2"],
                "tags": ["summary"]
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

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

        with patch("app.tools.note_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "note-123",
                "content": "Updated content with new insights...",
                "updated_at": "2024-01-02T00:00:00Z"
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

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

        with patch("app.tools.note_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "note-123",
                "tags": ["important", "review"]
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_update_note(params, user_id="user-123")

            assert result["success"] is True

    async def test_update_note_validates_ownership(self):
        """Test update_note validates user owns the note."""
        params = {
            "note_id": "note-123",
            "updates": {"content": "New content"}
        }

        with patch("app.tools.note_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)  # Note not found or not owned
            mock_db.return_value.__aenter__.return_value = mock_conn

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