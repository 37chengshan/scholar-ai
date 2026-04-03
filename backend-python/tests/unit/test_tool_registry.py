"""Unit tests for Tool Registry.

Tests the core tool registration and discovery system for Agent tools.

Test Categories:
- Tool registration and retrieval
- Tool schema validation
- Permission checking
- Tool listing
"""

import pytest
from typing import Any, Dict

from app.core.tool_registry import Tool, ToolRegistry


class TestTool:
    """Test Tool model."""

    def test_tool_creation(self):
        """Test creating a tool with all fields."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "required": True
                }
            },
            needs_confirmation=False
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert "query" in tool.parameters
        assert tool.needs_confirmation is False

    def test_tool_with_confirmation(self):
        """Test tool that needs confirmation."""
        tool = Tool(
            name="dangerous_tool",
            description="A dangerous operation",
            parameters={},
            needs_confirmation=True
        )

        assert tool.needs_confirmation is True


class TestToolRegistry:
    """Test Tool Registry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh ToolRegistry instance."""
        return ToolRegistry()

    def test_registry_initialization(self, registry):
        """Test 1: Tool Registry can register and retrieve tools."""
        # Registry should be initialized
        assert registry is not None

        # Register a tool
        tool = Tool(
            name="test_tool",
            description="Test tool",
            parameters={},
            needs_confirmation=False
        )
        registry.register(tool)

        # Retrieve the tool
        retrieved = registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_registry_lists_all_tools(self, registry):
        """Test 2: Tool Registry lists all 15 tools correctly."""
        # Get all tools
        tools = registry.list_all()

        # Should have at least 15 tools
        assert len(tools) >= 15, f"Expected at least 15 tools, got {len(tools)}"

        # Check for required tool categories
        tool_names = {t.name for t in tools}

        # Query tools (6)
        required_query_tools = [
            "external_search",
            "rag_search",
            "list_papers",
            "read_paper",
            "list_notes",
            "read_note"
        ]
        for tool_name in required_query_tools:
            assert tool_name in tool_names, f"Missing query tool: {tool_name}"

        # Note tools (3)
        required_note_tools = ["create_note", "update_note"]
        for tool_name in required_note_tools:
            assert tool_name in tool_names, f"Missing note tool: {tool_name}"

        # Paper tools (2)
        required_paper_tools = ["upload_paper", "delete_paper"]
        for tool_name in required_paper_tools:
            assert tool_name in tool_names, f"Missing paper tool: {tool_name}"

        # Advanced tools (3)
        required_advanced_tools = [
            "extract_references",
            "merge_documents",
            "execute_command"
        ]
        for tool_name in required_advanced_tools:
            assert tool_name in tool_names, f"Missing advanced tool: {tool_name}"

    def test_registry_identifies_tools_needing_confirmation(self, registry):
        """Test 3: Tool Registry identifies tools needing confirmation."""
        # Tools that need confirmation
        dangerous_tools = ["upload_paper", "delete_paper", "execute_command"]

        for tool_name in dangerous_tools:
            needs_confirm = registry.needs_confirmation(tool_name)
            assert needs_confirm is True, f"{tool_name} should need confirmation"

        # Tools that don't need confirmation
        safe_tools = ["external_search", "rag_search", "list_papers", "read_paper"]

        for tool_name in safe_tools:
            needs_confirm = registry.needs_confirmation(tool_name)
            assert needs_confirm is False, f"{tool_name} should not need confirmation"

    def test_tool_schemas_are_valid_json_schema(self, registry):
        """Test 4: Tool schemas are valid JSON Schema."""
        schemas = registry.list_tools_schema()

        assert len(schemas) >= 15, f"Expected at least 15 schemas, got {len(schemas)}"

        for schema in schemas:
            # Each schema should have required fields
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema

            function = schema["function"]
            assert "name" in function
            assert "description" in function
            assert "parameters" in function

            # Parameters should have properties and required fields
            params = function["parameters"]
            assert "type" in params
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    def test_get_nonexistent_tool(self, registry):
        """Test retrieving a tool that doesn't exist."""
        tool = registry.get("nonexistent_tool")
        assert tool is None

    def test_needs_confirmation_for_nonexistent_tool(self, registry):
        """Test confirmation check for nonexistent tool."""
        # Should return False for nonexistent tools
        needs_confirm = registry.needs_confirmation("nonexistent_tool")
        assert needs_confirm is False