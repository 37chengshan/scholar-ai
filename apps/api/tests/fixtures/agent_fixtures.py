"""Agent fixtures for integration tests.

Provides mock components for Agent Runner testing:
- Mock LLM client
- Mock tool registry with executors
- Mock safety layer
- Mock context manager
- Test session context

Reference: VALIDATION.md §9.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from typing import Any, Dict, List

from app.core.agent_runner import AgentRunner
from app.core.tool_registry import ToolRegistry, Tool
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager, Context, Message


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client for Agent execution."""
    client = MagicMock()
    return client


@pytest.fixture
async def tool_registry():
    """Create tool registry with mock executors."""
    registry = ToolRegistry()

    # Register mock executors for common tools
    async def mock_external_search(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "papers": [
                    {"id": "paper1", "title": "AI Paper 1"},
                    {"id": "paper2", "title": "AI Paper 2"}
                ]
            }
        }

    async def mock_rag_search(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "answer": f"Answer to: {params.get('question', '')}",
                "citations": ["citation1", "citation2"]
            }
        }

    async def mock_list_papers(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "papers": [
                    {"id": "paper1", "title": "Paper 1", "status": "completed"},
                    {"id": "paper2", "title": "Paper 2", "status": "completed"}
                ]
            }
        }

    async def mock_read_paper(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "paper_id": params.get("paper_id", ""),
                "title": "Test Paper",
                "abstract": "This is a test abstract",
                "content": "Test paper content"
            }
        }

    async def mock_create_note(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "note_id": "note123",
                "title": params.get("title", ""),
                "content": params.get("content", "")
            }
        }

    async def mock_delete_paper(params: Dict, **kwargs) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "deleted": True,
                "paper_id": params.get("paper_id", "")
            }
        }

    # Register executors
    registry.register_executor("external_search", mock_external_search)
    registry.register_executor("rag_search", mock_rag_search)
    registry.register_executor("list_papers", mock_list_papers)
    registry.register_executor("read_paper", mock_read_paper)
    registry.register_executor("create_note", mock_create_note)
    registry.register_executor("delete_paper", mock_delete_paper)

    return registry


@pytest.fixture
def safety_layer():
    """Create safety layer for permission checks."""
    return SafetyLayer()


@pytest.fixture
def context_manager():
    """Create context manager."""
    return ContextManager()


@pytest.fixture
async def agent_runner(mock_llm_client, tool_registry, context_manager, safety_layer):
    """Create agent runner with all dependencies."""
    return AgentRunner(
        llm_client=mock_llm_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=10
    )


@pytest.fixture
async def session_context():
    """Create test session context."""
    return {
        "session_id": "test_session_123",
        "user_id": "test_user_456",
        "messages": []
    }


@pytest.fixture
def mock_context():
    """Create mock execution context."""
    return Context(
        objective="Test objective",
        important_messages=[
            Message(role="user", content="Test user input")
        ],
        environment={
            "user_id": "test_user_456",
            "session_id": "test_session_123"
        }
    )