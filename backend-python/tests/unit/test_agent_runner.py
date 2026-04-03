"""Unit tests for Agent Runner.

Tests ReAct pattern implementation:
- Simple query execution (1 iteration)
- Multi-step workflow (3-5 iterations)
- Dangerous tool confirmation pause
- Max iteration limit enforcement
- Tool execution error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.agent_runner import AgentRunner, AgentState
from app.core.tool_registry import ToolRegistry, Tool
from app.core.safety_layer import SafetyLayer, PermissionLevel
from app.core.context_manager import ContextManager, Context, Message


@pytest.fixture
def tool_registry():
    """Create tool registry with mock tools."""
    registry = ToolRegistry()
    return registry


@pytest.fixture
def safety_layer():
    """Create safety layer."""
    return SafetyLayer()


@pytest.fixture
def context_manager():
    """Create context manager."""
    return ContextManager()


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    return client


@pytest.fixture
def agent_runner(mock_llm_client, tool_registry, context_manager, safety_layer):
    """Create agent runner with dependencies."""
    return AgentRunner(
        llm_client=mock_llm_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=10
    )


class TestAgentRunnerSimpleQuery:
    """Test 1: Agent executes simple query in 1 iteration."""
    
    @pytest.mark.asyncio
    async def test_simple_query_one_iteration(self, agent_runner):
        """Agent should complete simple query in 1 iteration."""
        # Mock context manager
        mock_context = Context(
            objective="Find papers about machine learning",
            important_messages=[
                Message(role="user", content="Find papers about machine learning")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to return final answer immediately
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": True,
                    "content": "I found 10 papers about machine learning in your library."
                }
            ):
                result = await agent_runner.execute(
                    user_input="Find papers about machine learning",
                    session_id="session123",
                    user_id="user123"
                )
        
        # Verify result
        assert result["success"] == True
        assert result["iterations"] == 1
        assert result["state"] == AgentState.COMPLETED.value
        assert "papers" in result["answer"]
        assert len(result["tool_calls"]) == 0


class TestAgentRunnerMultiStepWorkflow:
    """Test 2: Agent handles multi-step workflow (3-5 iterations)."""
    
    @pytest.mark.asyncio
    async def test_multi_step_workflow(self, agent_runner):
        """Agent should execute multi-step workflow with 3-5 iterations."""
        # Mock context
        mock_context = Context(
            objective="Find recent AI papers and create a summary note",
            important_messages=[
                Message(role="user", content="Find recent AI papers and create a summary note")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM responses for multi-step workflow
            think_responses = [
                # Iteration 1: Search papers
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "external_search",
                        "parameters": {"query": "AI", "limit": 10}
                    }
                },
                # Iteration 2: Read papers
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "read_paper",
                        "parameters": {"paper_id": "paper1"}
                    }
                },
                # Iteration 3: Create note
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "create_note",
                        "parameters": {
                            "title": "AI Papers Summary",
                            "content": "Summary of recent AI papers..."
                        }
                    }
                },
                # Iteration 4: Complete
                {
                    "is_complete": True,
                    "content": "I found 10 recent AI papers and created a summary note for you."
                }
            ]
            
            with patch.object(agent_runner, '_think', side_effect=think_responses):
                # Mock tool execution
                with patch.object(
                    agent_runner,
                    '_execute_tool',
                    return_value={
                        "success": True,
                        "data": {"result": "mock result"}
                    }
                ):
                    result = await agent_runner.execute(
                        user_input="Find recent AI papers and create a summary note",
                        session_id="session123",
                        user_id="user123"
                    )
        
        # Verify result
        assert result["success"] == True
        assert result["iterations"] == 4
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) == 3  # 3 tool calls before completion
        
        # Verify tool calls sequence
        tool_sequence = [tc["tool"] for tc in result["tool_calls"]]
        assert tool_sequence == ["external_search", "read_paper", "create_note"]


class TestAgentRunnerDangerousToolConfirmation:
    """Test 3: Agent pauses for confirmation on dangerous tool."""
    
    @pytest.mark.asyncio
    async def test_dangerous_tool_requires_confirmation(self, agent_runner):
        """Agent should pause when dangerous tool needs confirmation."""
        # Mock context
        mock_context = Context(
            objective="Delete old paper",
            important_messages=[
                Message(role="user", content="Delete old paper")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to select dangerous tool
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": False,
                    "tool_call": {
                        "name": "delete_paper",
                        "parameters": {"paper_id": "paper123"}
                    }
                }
            ):
                result = await agent_runner.execute(
                    user_input="Delete old paper",
                    session_id="session123",
                    user_id="user123",
                    auto_confirm=False  # Don't auto-confirm
                )
        
        # Verify result
        assert result["success"] == False
        assert result["needs_confirmation"] == True
        assert result["tool_name"] == "delete_paper"
        assert result["iterations"] == 1
        assert result["state"] == AgentState.WAITING_CONFIRMATION.value
        
        # Verify confirmation message
        assert "dangerous" in result["message"].lower()
        assert "confirmation" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_auto_confirm_dangerous_tool(self, agent_runner):
        """Agent should auto-confirm dangerous tool when enabled."""
        # Mock context
        mock_context = Context(
            objective="Delete old paper",
            important_messages=[
                Message(role="user", content="Delete old paper")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            think_responses = [
                # Iteration 1: Delete paper (dangerous)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "delete_paper",
                        "parameters": {"paper_id": "paper123"}
                    }
                },
                # Iteration 2: Complete
                {
                    "is_complete": True,
                    "content": "Paper deleted successfully."
                }
            ]
            
            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(
                    agent_runner,
                    '_execute_tool',
                    return_value={
                        "success": True,
                        "data": {"deleted": True}
                    }
                ):
                    result = await agent_runner.execute(
                        user_input="Delete old paper",
                        session_id="session123",
                        user_id="user123",
                        auto_confirm=True  # Auto-confirm dangerous operations
                    )
        
        # Verify result - should complete with auto-confirm
        assert result["success"] == True
        assert result["iterations"] == 2
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "delete_paper"


class TestAgentRunnerMaxIterations:
    """Test 4: Agent stops at max iterations (10)."""
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, agent_runner):
        """Agent should stop when max iterations reached."""
        # Set max iterations to 10
        agent_runner.max_iterations = 10
        
        # Mock context
        mock_context = Context(
            objective="Complex multi-step task",
            important_messages=[
                Message(role="user", content="Complex multi-step task")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to always request more tools (never complete)
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": False,
                    "tool_call": {
                        "name": "external_search",
                        "parameters": {"query": "test"}
                    }
                }
            ):
                with patch.object(
                    agent_runner,
                    '_execute_tool',
                    return_value={
                        "success": True,
                        "data": {"result": "mock"}
                    }
                ):
                    result = await agent_runner.execute(
                        user_input="Complex multi-step task",
                        session_id="session123",
                        user_id="user123"
                    )
        
        # Verify result - should fail at max iterations
        assert result["success"] == False
        assert result["iterations"] == 10
        assert result["state"] == AgentState.FAILED.value
        assert "max iterations" in result["error"].lower()
        assert len(result["tool_calls"]) == 10  # All iterations made tool calls


class TestAgentRunnerToolExecutionErrors:
    """Test 5: Agent handles tool execution errors."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_error_recovery(self, agent_runner):
        """Agent should handle tool errors and try alternative approach."""
        # Mock context
        mock_context = Context(
            objective="Search for papers",
            important_messages=[
                Message(role="user", content="Search for papers")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            think_responses = [
                # Iteration 1: Try external_search (fails)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "external_search",
                        "parameters": {"query": "AI"}
                    }
                },
                # Iteration 2: Try rag_search (succeeds)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "rag_search",
                        "parameters": {"question": "AI"}
                    }
                },
                # Iteration 3: Complete
                {
                    "is_complete": True,
                    "content": "Found papers using RAG search after external search failed."
                }
            ]
            
            execute_responses = [
                # First tool fails
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # Second tool succeeds
                {
                    "success": True,
                    "data": {"papers": ["paper1", "paper2"]}
                }
            ]
            
            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner, '_execute_tool', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="Search for papers",
                        session_id="session123",
                        user_id="user123"
                    )
        
        # Verify result - should recover from error
        assert result["success"] == True
        assert result["iterations"] == 3
        assert result["state"] == AgentState.COMPLETED.value
        
        # Verify tool calls
        assert len(result["tool_calls"]) == 2
        assert result["tool_calls"][0]["tool"] == "external_search"
        assert result["tool_calls"][0]["result"]["success"] == False
        assert result["tool_calls"][1]["tool"] == "rag_search"
        assert result["tool_calls"][1]["result"]["success"] == True
    
    @pytest.mark.asyncio
    async def test_tool_not_found_error(self, agent_runner):
        """Agent should handle tool not found error."""
        # Mock context
        mock_context = Context(
            objective="Use unknown tool",
            important_messages=[
                Message(role="user", content="Use unknown tool")
            ],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to request unknown tool
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": False,
                    "tool_call": {
                        "name": "unknown_tool",
                        "parameters": {}
                    }
                }
            ):
                result = await agent_runner.execute(
                    user_input="Use unknown tool",
                    session_id="session123",
                    user_id="user123"
                )
        
        # Verify result
        assert result["success"] == False
        assert result["iterations"] == 1
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["result"]["success"] == False
        assert "not found" in result["tool_calls"][0]["result"]["error"]


class TestAgentRunnerResumeWithTool:
    """Test resume after user confirmation."""
    
    @pytest.mark.asyncio
    async def test_resume_with_confirmed_tool(self, agent_runner):
        """Agent should resume execution after user confirms dangerous tool."""
        # Mock context
        mock_context = Context(
            objective="Delete paper",
            important_messages=[],
            environment={"session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            with patch.object(
                agent_runner,
                '_execute_tool',
                return_value={
                    "success": True,
                    "data": {"deleted": True}
                }
            ):
                result = await agent_runner.resume_with_tool(
                    session_id="session123",
                    tool_name="delete_paper",
                    parameters={"paper_id": "paper123"},
                    confirmed=True
                )
        
        # Verify result
        assert result["success"] == True
        assert result["state"] == AgentState.TOOL_EXECUTION.value
        assert result["tool_result"]["success"] == True
    
    @pytest.mark.asyncio
    async def test_resume_with_declined_tool(self, agent_runner):
        """Agent should handle user declining tool execution."""
        result = await agent_runner.resume_with_tool(
            session_id="session123",
            tool_name="delete_paper",
            parameters={"paper_id": "paper123"},
            confirmed=False
        )
        
        # Verify result
        assert result["success"] == False
        assert result["state"] == AgentState.PAUSED.value
        assert "declined" in result["error"].lower()


class TestAgentRunnerStateTransitions:
    """Test agent state transitions during execution."""
    
    @pytest.mark.asyncio
    async def test_state_transitions_logged(self, agent_runner):
        """Agent should log all state transitions."""
        # Mock context
        mock_context = Context(
            objective="Simple query",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": True,
                    "content": "Done"
                }
            ):
                initial_state = agent_runner.current_state
                result = await agent_runner.execute(
                    user_input="Simple query",
                    session_id="session123",
                    user_id="user123"
                )
                final_state = agent_runner.current_state
        
        # Verify state transitions
        assert initial_state == AgentState.IDLE
        assert final_state == AgentState.COMPLETED