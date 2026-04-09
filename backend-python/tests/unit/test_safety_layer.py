"""Unit tests for Safety Layer.

Tests the 3-level permission control system for Agent tools.

Test Categories:
- Permission level classification
- Auto-approval for read operations
- Audit logging for write operations
- Confirmation requirement for dangerous operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.safety_layer import SafetyLayer, PermissionLevel


class TestPermissionLevel:
    """Test PermissionLevel enum."""

    def test_permission_levels_exist(self):
        """Test that all permission levels are defined."""
        assert PermissionLevel.READ.value == 1
        assert PermissionLevel.WRITE.value == 2
        assert PermissionLevel.DANGEROUS.value == 3


class TestSafetyLayer:
    """Test Safety Layer functionality."""

    @pytest.fixture
    def safety_layer(self):
        """Create a SafetyLayer instance."""
        return SafetyLayer()

    def test_tool_permissions_mapping(self, safety_layer):
        """Test that tool permissions are correctly mapped."""
        # Level 1: READ operations
        read_tools = [
            "external_search",
            "rag_search",
            "list_papers",
            "read_paper",
            "list_notes",
            "read_note"
        ]
        for tool_name in read_tools:
            level = safety_layer.TOOL_PERMISSIONS.get(tool_name)
            assert level == PermissionLevel.READ, f"{tool_name} should be READ level"

        # Level 2: WRITE operations
        write_tools = [
            "create_note",
            "update_note",
            "merge_documents",
            "extract_references"
        ]
        for tool_name in write_tools:
            level = safety_layer.TOOL_PERMISSIONS.get(tool_name)
            assert level == PermissionLevel.WRITE, f"{tool_name} should be WRITE level"

        # Level 3: DANGEROUS operations
        dangerous_tools = [
            "upload_paper",
            "delete_paper",
            "execute_command"
        ]
        for tool_name in dangerous_tools:
            level = safety_layer.TOOL_PERMISSIONS.get(tool_name)
            assert level == PermissionLevel.DANGEROUS, f"{tool_name} should be DANGEROUS level"

    @pytest.mark.asyncio
    async def test_read_operations_auto_approved(self, safety_layer):
        """Test 1: Read operations auto-approved."""
        context = {
            "user_id": "test-user",
            "session_id": "test-session"
        }

        # Test a read operation
        result = await safety_layer.check_permission("external_search", context)

        assert result["allowed"] is True
        assert result["needs_confirmation"] is False

    @pytest.mark.asyncio
    async def test_write_operations_logged(self, safety_layer):
        """Test 2: Write operations logged but auto-approved."""
        context = {
            "user_id": "test-user",
            "session_id": "test-session"
        }

        # Mock the log_audit method
        with patch.object(safety_layer, 'log_audit', new_callable=AsyncMock) as mock_log:
            result = await safety_layer.check_permission("create_note", context)

            # Should be allowed
            assert result["allowed"] is True
            assert result["needs_confirmation"] is False

            # Should have logged audit
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_dangerous_operations_require_confirmation(self, safety_layer):
        """Test 3: Dangerous operations require confirmation."""
        context = {
            "user_id": "test-user",
            "session_id": "test-session"
        }

        # Test a dangerous operation
        result = await safety_layer.check_permission("delete_paper", context)

        assert result["allowed"] is False
        assert result["needs_confirmation"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_audit_log_created(self, safety_layer):
        """Test 4: Audit log created for write operations."""
        context = {
            "user_id": "test-user",
            "session_id": "test-session",
            "tool_name": "create_note",
            "parameters": {"title": "Test Note"}
        }

        # Mock SQLAlchemy session
        with patch('app.core.safety_layer.AsyncSessionLocal') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session

            await safety_layer.log_audit("create_note", context)

            # Verify session.add was called with an AuditLog object
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_tool_defaults_to_read(self, safety_layer):
        """Test that unknown tools default to READ permission."""
        context = {
            "user_id": "test-user",
            "session_id": "test-session"
        }

        result = await safety_layer.check_permission("unknown_tool", context)

        # Unknown tools should be treated as READ (safest default)
        assert result["allowed"] is True
        assert result["needs_confirmation"] is False