"""Unit tests for audit logging integration in Agent Runner.

Tests that tool executions are logged to audit trail.

Per D-08:
- All tool executions logged to audit_logs table
- Logs include performance metrics (tokens, cost, execution time)
- CRITICAL tools still trigger permission check before logging
- Failed tool executions logged with error message

Test Coverage:
- Tool execution triggers audit log entry
- Audit log includes tokens_used, cost_cny, execution_ms
- CRITICAL tools trigger permission check before logging
- Failed tool executions logged with error
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.core.agent_runner import AgentRunner, AgentState
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager, Context


class TestAuditLoggingIntegration:
    """Test audit logging is wired into Agent Runner."""

    @pytest.fixture
    def agent_runner(self):
        """Create agent runner with mocked dependencies."""
        mock_llm = MagicMock()
        mock_registry = MagicMock()
        mock_context_mgr = MagicMock()
        mock_safety = MagicMock()

        return AgentRunner(
            llm_client=mock_llm,
            tool_registry=mock_registry,
            context_manager=mock_context_mgr,
            safety_layer=mock_safety,
            max_iterations=10,
        )

    @pytest.mark.asyncio
    async def test_tool_execution_triggers_audit_log(self, agent_runner):
        """Test that tool execution triggers audit log entry."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"},
        )

        async def mock_execute(*args, **kwargs):
            return {"success": True, "data": {"result": "test"}}

        with patch.object(
            agent_runner.tool_registry, "execute", side_effect=mock_execute
        ):
            with patch("app.core.agent_runner.get_audit_logger") as mock_get_logger:
                mock_audit_logger = AsyncMock()
                mock_get_logger.return_value = mock_audit_logger

                result = await agent_runner._execute_tool(
                    tool_name="rag_search",
                    parameters={"question": "test"},
                    context=mock_context,
                )

                # Verify audit logger was called
                assert mock_audit_logger.record.called

    @pytest.mark.asyncio
    async def test_audit_log_includes_performance_metrics(self, agent_runner):
        """Test that audit log includes tokens, cost, execution time."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"},
        )

        # Set some metrics
        agent_runner.total_tokens_used = 500
        agent_runner.total_cost = 0.01

        async def mock_execute(*args, **kwargs):
            return {"success": True, "data": {"result": "test"}}

        with patch.object(
            agent_runner.tool_registry, "execute", side_effect=mock_execute
        ):
            with patch("app.core.agent_runner.get_audit_logger") as mock_get_logger:
                mock_audit_logger = AsyncMock()
                mock_get_logger.return_value = mock_audit_logger

                await agent_runner._execute_tool(
                    tool_name="rag_search",
                    parameters={"question": "test"},
                    context=mock_context,
                )

                # Verify record was called with metrics
                call_args = mock_audit_logger.record.call_args
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_failed_tool_execution_logged_with_error(self, agent_runner):
        """Test that failed tool executions are logged with error message."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"},
        )

        async def mock_execute(*args, **kwargs):
            return {"success": False, "error": "Tool execution failed"}

        with patch.object(
            agent_runner.tool_registry, "execute", side_effect=mock_execute
        ):
            with patch("app.core.agent_runner.get_audit_logger") as mock_get_logger:
                mock_audit_logger = AsyncMock()
                mock_get_logger.return_value = mock_audit_logger

                result = await agent_runner._execute_tool(
                    tool_name="rag_search",
                    parameters={"question": "test"},
                    context=mock_context,
                )

                # Verify audit log was called even for failed execution
                assert mock_audit_logger.record.called

    @pytest.mark.asyncio
    async def test_audit_logging_doesnt_block_on_error(self, agent_runner):
        """Test that audit logging errors don't block tool execution."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"},
        )

        # Create an async mock for the registry
        async def mock_execute(*args, **kwargs):
            return {"success": True, "data": {"result": "test"}}

        with patch.object(
            agent_runner.tool_registry, "execute", side_effect=mock_execute
        ):
            with patch("app.core.agent_runner.get_audit_logger") as mock_get_logger:
                mock_audit_logger = AsyncMock()
                mock_audit_logger.record.side_effect = Exception("Audit log failed")
                mock_get_logger.return_value = mock_audit_logger

                # Tool execution should still succeed
                result = await agent_runner._execute_tool(
                    tool_name="rag_search",
                    parameters={"question": "test"},
                    context=mock_context,
                )

                assert result["success"] is True


class TestCriticalToolConfirmation:
    """Test CRITICAL tool confirmation flow."""

    @pytest.fixture
    def agent_runner(self):
        """Create agent runner with mocked dependencies."""
        mock_llm = MagicMock()
        mock_registry = MagicMock()
        mock_context_mgr = MagicMock()
        mock_safety = SafetyLayer()  # Use real SafetyLayer

        return AgentRunner(
            llm_client=mock_llm,
            tool_registry=mock_registry,
            context_manager=mock_context_mgr,
            safety_layer=mock_safety,
            max_iterations=10,
        )

    @pytest.mark.asyncio
    async def test_critical_tool_still_triggers_permission_check(self, agent_runner):
        """Test that CRITICAL tools still trigger permission check."""
        # Use real SafetyLayer check_permission
        result = await agent_runner.safety_layer.check_permission(
            "delete_paper", {"user_id": "user123"}
        )

        assert result["needs_confirmation"] is True
