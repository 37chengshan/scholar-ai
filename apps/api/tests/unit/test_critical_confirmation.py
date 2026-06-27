"""Unit tests for the current Safety Layer permission contract."""

import pytest

from app.core.safety_layer import SafetyLayer, PermissionLevel


class TestCriticalToolConfirmation:
    """Test CRITICAL tool confirmation in Safety Layer."""

    @pytest.fixture
    def safety_layer(self):
        return SafetyLayer()

    @pytest.mark.asyncio
    async def test_delete_paper_needs_confirmation(self, safety_layer):
        result = await safety_layer.check_permission(
            "delete_paper", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is False
        assert result["needs_confirmation"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_execute_command_needs_confirmation(self, safety_layer):
        result = await safety_layer.check_permission(
            "execute_command", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is False
        assert result["needs_confirmation"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_rag_search_no_confirmation_needed(self, safety_layer):
        result = await safety_layer.check_permission(
            "rag_search", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is True
        assert result["needs_confirmation"] is False

    @pytest.mark.asyncio
    async def test_external_search_no_confirmation_needed(self, safety_layer):
        result = await safety_layer.check_permission(
            "external_search", {"user_id": "user123", "session_id": "session123"}
        )

        assert result["allowed"] is True
        assert result["needs_confirmation"] is False


class TestDangerousToolMessages:
    @pytest.fixture
    def safety_layer(self):
        return SafetyLayer()

    @pytest.mark.asyncio
    async def test_delete_paper_confirmation_message(self, safety_layer):
        result = await safety_layer.check_permission(
            "delete_paper",
            {"user_id": "user123", "parameters": {"title": "Test Paper"}},
        )

        assert result["needs_confirmation"] is True
        assert "message" in result
        assert "dangerous operation" in result["message"].lower()
        assert "delete_paper" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_command_confirmation_message(self, safety_layer):
        result = await safety_layer.check_permission(
            "execute_command", {"user_id": "user123", "parameters": {"command": "ls"}}
        )

        assert result["needs_confirmation"] is True
        assert "message" in result
        assert "dangerous operation" in result["message"].lower()
        assert "execute_command" in result["message"]


class TestToolPermissions:
    def test_tool_permissions_mapping_exists(self):
        safety = SafetyLayer()

        assert hasattr(safety, "TOOL_PERMISSIONS")
        assert isinstance(safety.TOOL_PERMISSIONS, dict)

    def test_tool_permissions_contains_delete_paper(self):
        safety = SafetyLayer()

        assert safety.TOOL_PERMISSIONS["delete_paper"] == PermissionLevel.DANGEROUS

    def test_tool_permissions_contains_execute_command(self):
        safety = SafetyLayer()

        assert safety.TOOL_PERMISSIONS["execute_command"] == PermissionLevel.DANGEROUS
