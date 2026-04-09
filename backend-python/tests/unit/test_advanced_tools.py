"""Unit tests for advanced tool implementations.

Tests cover:
- extract_references: Citation extraction
- merge_documents: Document merging (placeholder)
- execute_command: Tool chain execution
- show_message: User message display
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.advanced_tools import (
    execute_extract_references,
    execute_merge_documents,
    execute_execute_command,
    execute_show_message,
)


@pytest.mark.asyncio
class TestExtractReferences:
    """Tests for extract_references tool."""

    async def test_extract_references_basic(self):
        """Test basic reference extraction."""
        params = {
            "paper_ids": ["paper-1"],
            "format": "apa"
        }

        with patch("app.tools.advanced_tools.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_paper = MagicMock()
            mock_paper.title = "Test Paper"
            mock_paper.content = "References\n[1] Author A. (2020). Title B. Journal C.\n[2] Author D. (2021). Title E. Journal F."
            mock_result.first = MagicMock(return_value=mock_paper)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value.__aenter__.return_value = mock_session

            result = await execute_extract_references(params, user_id="user-123")

            assert result["success"] is True
            assert "references" in result["data"]

    async def test_extract_references_empty_paper_ids(self):
        """Test empty paper_ids returns error."""
        params = {"paper_ids": [], "format": "apa"}
        result = await execute_extract_references(params)
        assert result["success"] is False
        assert "required" in result["error"].lower()

    async def test_extract_references_bibtex_format(self):
        """Test BibTeX format output."""
        params = {
            "paper_ids": ["paper-1"],
            "format": "bibtex"
        }

        with patch("app.tools.advanced_tools.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_paper = MagicMock()
            mock_paper.title = "Test"
            mock_paper.content = "References\nSmith, J. (2020). Testing. Journal."
            mock_result.first = MagicMock(return_value=mock_paper)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value.__aenter__.return_value = mock_session

            result = await execute_extract_references(params, user_id="user-123")

            assert result["success"] is True
            assert result["data"]["format"] == "bibtex"

    async def test_extract_references_paper_not_found(self):
        """Test handling when paper not found."""
        params = {"paper_ids": ["non-existent"], "format": "apa"}

        with patch("app.tools.advanced_tools.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value.__aenter__.return_value = mock_session

            result = await execute_extract_references(params, user_id="user-123")

            assert result["success"] is True  # Continues with empty
            assert result["data"]["total_count"] == 0

    async def test_extract_references_no_references_section(self):
        """Test paper without references section."""
        params = {"paper_ids": ["paper-1"], "format": "apa"}

        with patch("app.tools.advanced_tools.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_paper = MagicMock()
            mock_paper.title = "Test"
            mock_paper.content = "No references here."
            mock_result.first = MagicMock(return_value=mock_paper)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value.__aenter__.return_value = mock_session

            result = await execute_extract_references(params, user_id="user-123")

            assert result["success"] is True
            assert result["data"]["references"] == []


@pytest.mark.asyncio
class TestExecuteCommand:
    """Tests for execute_command tool."""
    
    async def test_execute_command_basic_chain(self):
        """Test basic tool chain execution."""
        params = {
            "command": "list_papers → create_note",
            "args": {"limit": 5}
        }
        
        mock_registry = MagicMock()
        mock_registry.get = MagicMock(return_value=MagicMock(needs_confirmation=False))
        mock_registry.execute = AsyncMock(return_value={
            "success": True,
            "data": {"papers": [{"id": "p1"}]}
        })
        
        result = await execute_execute_command(
            params,
            user_id="user-123",
            tool_registry=mock_registry
        )
        
        assert result["success"] is True
    
    async def test_execute_command_empty_command(self):
        """Test empty command returns error."""
        params = {"command": "", "args": {}}
        result = await execute_execute_command(params)
        assert result["success"] is False
        assert "required" in result["error"].lower()
    
    async def test_execute_command_invalid_tool(self):
        """Test invalid tool name in chain."""
        params = {
            "command": "nonexistent_tool",
            "args": {}
        }
        
        mock_registry = MagicMock()
        mock_registry.get = MagicMock(return_value=None)
        
        result = await execute_execute_command(
            params,
            user_id="user-123",
            tool_registry=mock_registry
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    async def test_execute_command_tool_needs_confirmation(self):
        """Test tool requiring confirmation pauses chain."""
        params = {
            "command": "delete_paper",
            "args": {"paper_id": "p1"}
        }
        
        mock_registry = MagicMock()
        mock_registry.get = MagicMock(return_value=MagicMock(needs_confirmation=True))
        
        result = await execute_execute_command(
            params,
            user_id="user-123",
            tool_registry=mock_registry
        )
        
        assert result["success"] is False
        assert result.get("needs_confirmation") is True
    
    async def test_execute_command_tool_failure(self):
        """Test tool failure stops chain."""
        params = {
            "command": "list_papers → create_note",
            "args": {}
        }
        
        mock_registry = MagicMock()
        mock_registry.get = MagicMock(return_value=MagicMock(needs_confirmation=False))
        mock_registry.execute = AsyncMock(return_value={
            "success": False,
            "error": "Database error"
        })
        
        result = await execute_execute_command(
            params,
            user_id="user-123",
            tool_registry=mock_registry
        )
        
        assert result["success"] is False
        assert "failed" in result["error"].lower()
    
    async def test_execute_command_no_registry(self):
        """Test missing registry handling."""
        params = {"command": "list_papers", "args": {}}
        result = await execute_execute_command(params, user_id="user-123")
        assert result["success"] is False


@pytest.mark.asyncio
class TestShowMessage:
    """Tests for show_message tool."""
    
    async def test_show_message_info(self):
        """Test info message."""
        params = {"message": "Processing...", "type": "info"}
        result = await execute_show_message(params)
        assert result["success"] is True
        assert result["data"]["type"] == "info"
    
    async def test_show_message_warning(self):
        """Test warning message."""
        params = {"message": "Warning!", "type": "warning"}
        result = await execute_show_message(params)
        assert result["success"] is True
    
    async def test_show_message_success(self):
        """Test success message."""
        params = {"message": "Done!", "type": "success"}
        result = await execute_show_message(params)
        assert result["success"] is True
    
    async def test_show_message_progress(self):
        """Test progress message."""
        params = {"message": "50% complete", "type": "progress"}
        result = await execute_show_message(params)
        assert result["success"] is True


@pytest.mark.asyncio
class TestMergeDocuments:
    """Tests for merge_documents tool (placeholder)."""
    
    async def test_merge_documents_basic(self):
        """Test basic document merge."""
        params = {
            "sources": [
                {"type": "paper", "id": "p1"},
                {"type": "note", "id": "n1"}
            ],
            "output_format": "markdown"
        }
        
        result = await execute_merge_documents(params)
        
        # Placeholder returns success with message
        assert result["success"] is True
    
    async def test_merge_documents_empty_sources(self):
        """Test with empty sources."""
        params = {"sources": [], "output_format": "markdown"}
        result = await execute_merge_documents(params)
        assert result["success"] is True