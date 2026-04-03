"""Unit tests for agent initialization.

Tests verify:
- initialize_agent_components() returns correct tuple structure
- ToolRegistry has 15 registered executors
- Function imports and executes without errors
"""

import pytest
from typing import Tuple

from app.utils.agent_init import initialize_agent_components
from app.core.agent_runner import AgentRunner
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager


class TestAgentInit:
    """Test suite for agent initialization."""

    def test_returns_tuple_structure(self):
        """Test that initialize_agent_components() returns correct tuple structure."""
        result = initialize_agent_components()

        # Verify tuple structure
        assert isinstance(result, tuple)
        assert len(result) == 4

        # Verify each component type
        runner, registry, safety_layer, context_manager = result

        assert isinstance(runner, AgentRunner)
        assert isinstance(registry, ToolRegistry)
        assert isinstance(safety_layer, SafetyLayer)
        assert isinstance(context_manager, ContextManager)

    def test_registry_has_registered_executors(self):
        """Test that returned ToolRegistry has 15 registered executors."""
        runner, registry, safety_layer, context_manager = initialize_agent_components()

        # Verify registry has tools
        assert len(registry.tools) > 0

        # Verify 15 tools are registered
        assert len(registry.tools) == 15

        # Verify specific tools exist
        all_tools = registry.list_all()
        tool_names = [tool.name for tool in all_tools]
        expected_tools = [
            "external_search",
            "rag_search",
            "list_papers",
            "read_paper",
            "list_notes",
            "read_note",
            "create_note",
            "update_note",
            "ask_user_confirmation",
            "upload_paper",
            "delete_paper",
            "extract_references",
            "merge_documents",
            "execute_command",
            "show_message",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found in registry"

        # Verify executors are registered
        assert len(registry.executors) == 15
        for tool_name in expected_tools:
            assert tool_name in registry.executors, f"Executor for {tool_name} not registered"

    def test_import_success(self):
        """Test that function imports and executes without errors."""
        # This test verifies the import chain works
        from app.utils.agent_init import initialize_agent_components

        # Execute function
        result = initialize_agent_components()

        # Verify execution completed
        assert result is not None
        assert isinstance(result, tuple)

    def test_runner_has_correct_dependencies(self):
        """Test that AgentRunner has all dependencies wired correctly."""
        runner, registry, safety_layer, context_manager = initialize_agent_components()

        # Verify runner has all dependencies
        assert runner.llm_client is not None
        assert runner.tool_registry is not None
        assert runner.context_manager is not None
        assert runner.safety_layer is not None

        # Verify runner uses the same instances
        assert runner.tool_registry == registry
        assert runner.context_manager == context_manager
        assert runner.safety_layer == safety_layer

    def test_max_iterations_parameter(self):
        """Test that max_iterations parameter is correctly passed."""
        custom_iterations = 5

        runner, registry, safety_layer, context_manager = initialize_agent_components(
            max_iterations=custom_iterations
        )

        # Verify runner has custom max_iterations
        assert runner.max_iterations == custom_iterations