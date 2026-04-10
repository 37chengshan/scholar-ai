"""Unit tests for CRITICAL tool confirmation in Safety Layer.

Tests that CRITICAL tools trigger user confirmation.

Per D-07:
- Only CRITICAL risk tools need user confirmation
- CRITICAL_TOOLS: delete_paper, execute_command
- check_permission() returns needs_confirmation=true for CRITICAL tools
- PermissionResult includes confirmation_message for CRITICAL tools

Test Coverage:
- check_permission() returns needs_confirmation=true for delete_paper
- check_permission() returns needs_confirmation=true for execute_command
- check_permission() returns needs_confirmation=false for rag_search (LOW risk)
- PermissionResult includes confirmation_message for CRITICAL tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.safety_layer import SafetyLayer, PermissionLevel


class TestCriticalToolConfirmation:
    """Test CRITICAL tool confirmation in Safety Layer."""

    @pytest.fixture
    def safety_layer(self):
        """Create SafetyLayer instance."""
        return SafetyLayer()

    @pytest.mark.asyncio
    async def test_delete_paper_needs_confirmation(self, safety_layer):
        """Test that delete_paper tool requires user confirmation."""
        result = await safety_layer.check_permission(
            "delete_paper", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is False
        assert result["needs_confirmation"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_execute_command_needs_confirmation(self, safety_layer):
        """Test that execute_command tool requires user confirmation."""
        result = await safety_layer.check_permission(
            "execute_command", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is False
        assert result["needs_confirmation"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_rag_search_no_confirmation_needed(self, safety_layer):
        """Test that rag_search (LOW risk) doesn't need confirmation."""
        result = await safety_layer.check_permission(
            "rag_search", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is True
        assert result["needs_confirmation"] is False

    @pytest.mark.asyncio
    async def test_external_search_no_confirmation_needed(self, safety_layer):
        """Test that external_search (LOW risk) doesn't need confirmation."""
        result = await safety_layer.check_permission(
            "external_search", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is True
        assert result["needs_confirmation"] is False


class TestConfirmationMessage:
    """Test confirmation messages for CRITICAL tools."""

    @pytest.fixture
    def safety_layer(self):
        """Create SafetyLayer instance."""
        return SafetyLayer()

    @pytest.mark.asyncio
    async def test_delete_paper_confirmation_message(self, safety_layer):
        """Test that delete_paper has tool-specific confirmation message."""
        result = await safety_layer.check_permission(
            "delete_paper",
            {"user_id": "user123", "parameters": {"title": "Test Paper"}},
        )

        assert result["needs_confirmation"] is True
        assert "message" in result
        # Message should mention delete or cannot be undone
        assert (
            "delete" in result["message"].lower()
            or "cannot" in result["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_execute_command_confirmation_message(self, safety_layer):
        """Test that execute_command has tool-specific confirmation message."""
        result = await safety_layer.check_permission(
            "execute_command", {"user_id": "user123", "parameters": {"command": "ls"}}
        )

        assert result["needs_confirmation"] is True
        assert "message" in result
        # Message should mention command or system
        assert (
            "command" in result["message"].lower()
            or "system" in result["message"].lower()
        )

    def test_get_confirmation_message_delete_paper(self, safety_layer):
        """Test get_confirmation_message for delete_paper."""
        message = safety_layer.get_confirmation_message(
            "delete_paper", {"title": "Machine Learning Paper"}
        )

        assert "delete" in message.lower() or "cannot" in message.lower()
        assert "Machine Learning Paper" in message

    def test_get_confirmation_message_execute_command(self, safety_layer):
        """Test get_confirmation_message for execute_command."""
        message = safety_layer.get_confirmation_message(
            "execute_command", {"command": "rm -rf /data"}
        )

        assert "command" in message.lower()
        assert "rm -rf /data" in message


class TestCriticalToolsList:
    """Test CRITICAL_TOOLS list definition."""

    def test_critical_tools_list_exists(self):
        """Test that CRITICAL_TOOLS list is defined."""
        safety = SafetyLayer()

        assert hasattr(safety, "CRITICAL_TOOLS")
        assert isinstance(safety.CRITICAL_TOOLS, list)

    def test_critical_tools_contains_delete_paper(self):
        """Test that delete_paper is in CRITICAL_TOOLS."""
        safety = SafetyLayer()

        assert "delete_paper" in safety.CRITICAL_TOOLS

    def test_critical_tools_contains_execute_command(self):
        """Test that execute_command is in CRITICAL_TOOLS."""
        safety = SafetyLayer()

        assert "execute_command" in safety.CRITICAL_TOOLS
