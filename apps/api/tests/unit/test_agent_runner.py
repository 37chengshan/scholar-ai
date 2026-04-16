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
                # external_search retry 1: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # external_search retry 2: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # external_search retry 3: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # alternative rag_search: succeed
                {
                    "success": True,
                    "data": {"papers": ["paper1", "paper2"]}
                },
                # LLM iteration 2 rag_search: succeed
                {
                    "success": True,
                    "data": {"papers": ["paper3"]}
                }
            ]
            
            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner.tool_registry, 'execute', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="Search for papers",
                        session_id="session123",
                        user_id="user123"
                    )
        
        # Verify result - should recover from error using fallback
        assert result["success"] == True
        assert result["iterations"] == 3
        assert result["state"] == AgentState.COMPLETED.value
        
        # Verify tool calls
        assert len(result["tool_calls"]) >= 2
        assert result["tool_calls"][0]["tool"] == "external_search"
        # First tool used alternative (fallback mechanism)
        assert result["tool_calls"][0]["result"].get("used_alternative") is True
        assert result["tool_calls"][1]["tool"] == "rag_search"
    
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


class TestSystemPrompt:
    """Test system prompt enhancement with reasoning framework per D-11."""
    
    def test_system_prompt_includes_reasoning_steps(self, agent_runner):
        """System prompt should include explicit reasoning framework (Analyze → Select → Plan → Verify)."""
        mock_context = Context(
            objective="Find papers about AI",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        prompt = agent_runner._build_system_prompt(mock_context)
        
        # Verify reasoning framework is present
        assert "ANALYZE" in prompt or "analyze" in prompt.lower()
        assert "SELECT" in prompt or "select" in prompt.lower()
        assert "PLAN" in prompt or "plan" in prompt.lower()
        assert "VERIFY" in prompt or "verify" in prompt.lower()
    
    def test_system_prompt_guides_tool_selection(self, agent_runner):
        """System prompt should guide tool selection decisions."""
        mock_context = Context(
            objective="Search for papers",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        prompt = agent_runner._build_system_prompt(mock_context)
        
        # Verify tool selection guidance is present
        assert "tool" in prompt.lower()
        # Should mention deciding which tools to use
        assert "decide" in prompt.lower() or "select" in prompt.lower() or "choose" in prompt.lower()
    
    def test_system_prompt_includes_error_handling_guidance(self, agent_runner):
        """System prompt should include error handling strategy guidance."""
        mock_context = Context(
            objective="Test objective",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        prompt = agent_runner._build_system_prompt(mock_context)
        
        # Verify error handling guidance is present
        assert "error" in prompt.lower() or "fail" in prompt.lower()
        # Should mention retry or alternative strategies
        assert "retry" in prompt.lower() or "alternative" in prompt.lower() or "recover" in prompt.lower()


class TestErrorRecovery:
    """Test multi-layer error recovery per D-12."""
    
    def test_is_retryable_error_detects_transient_errors(self, agent_runner):
        """Agent should detect transient errors that can be retried."""
        # Network timeout is retryable
        assert agent_runner._is_retryable_error("timeout while connecting to server")
        assert agent_runner._is_retryable_error("network error: connection refused")
        assert agent_runner._is_retryable_error("service unavailable")
        
        # Non-retryable errors should return False
        assert not agent_runner._is_retryable_error("paper not found")
        assert not agent_runner._is_retryable_error("permission denied")
        assert not agent_runner._is_retryable_error("invalid parameter")
        assert not agent_runner._is_retryable_error("required field missing")
    
    def test_get_alternative_tool_returns_fallback(self, agent_runner):
        """Agent should get alternative tool for failed tools."""
        # external_search -> rag_search fallback
        alternative = agent_runner._get_alternative_tool("external_search")
        assert alternative == "rag_search"
        
        # rag_search -> external_search fallback (bidirectional)
        alternative = agent_runner._get_alternative_tool("rag_search")
        assert alternative == "external_search"
        
        # Tools without alternatives should return None
        alternative = agent_runner._get_alternative_tool("unknown_tool")
        assert alternative is None
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_retry_on_transient_error(self, agent_runner):
        """Agent should retry on transient errors before trying alternative."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        # Mock tool registry execute to fail with transient error then succeed
        call_count = [0]  # Use list to allow modification in nested function
        async def mock_execute(tool_name, params, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return {"success": False, "error": "timeout", "data": None}
            return {"success": True, "data": {"result": "success"}, "error": None}
        
        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute):
            result = await agent_runner._execute_with_fallback(
                tool_name="external_search",
                params={"query": "AI"},
                context=mock_context
            )
        
        # Should succeed after retry
        assert result["success"] == True
        assert call_count[0] >= 3  # At least 3 attempts (initial + 2 retries)
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_alternative_tool_on_permanent_failure(self, agent_runner):
        """Agent should try alternative tool when retries exhausted."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        # Mock external_search to always fail, rag_search to succeed
        async def mock_execute(tool_name, params, **kwargs):
            if tool_name == "external_search":
                return {"success": False, "error": "service permanently unavailable", "data": None}
            elif tool_name == "rag_search":
                return {"success": True, "data": {"papers": ["paper1"]}, "error": None}
            return {"success": False, "error": "unknown tool", "data": None}
        
        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute):
            result = await agent_runner._execute_with_fallback(
                tool_name="external_search",
                params={"query": "AI"},
                context=mock_context
            )
        
        # Should succeed using alternative tool
        assert result["success"] == True
        assert result["used_alternative"] == True
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_needs_user_decision_when_all_fail(self, agent_runner):
        """Agent should return needs_user_decision when all recovery options exhausted."""
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        # Mock both tools to fail
        async def mock_execute(tool_name, params, **kwargs):
            return {"success": False, "error": "service unavailable", "data": None}
        
        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute):
            result = await agent_runner._execute_with_fallback(
                tool_name="external_search",
                params={"query": "AI"},
                context=mock_context
            )
        
        # Should indicate user decision needed
        assert result["success"] == False
        assert result.get("needs_user_decision") == True
        assert "error" in result
        assert "suggestion" in result or "alternatives" in result
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, agent_runner):
        """Agent should retry with exponential backoff (1s, 2s, 4s)."""
        import asyncio
        import time
        
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={"user_id": "user123", "session_id": "session123"}
        )
        
        call_times = []
        async def mock_execute(tool_name, params, **kwargs):
            call_times.append(time.time())
            return {"success": False, "error": "timeout", "data": None}
        
        # Only test first few retries (not full exhaustion)
        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute):
            start_time = time.time()
            
            # We need to capture the retry delays
            # For testing, we'll patch asyncio.sleep to track delays
            sleep_delays = []
            async def mock_sleep(delay):
                sleep_delays.append(delay)
                # Don't actually sleep in tests
                return
            
            with patch('asyncio.sleep', side_effect=mock_sleep):
                result = await agent_runner._execute_with_fallback(
                    tool_name="external_search",
                    params={"query": "AI"},
                    context=mock_context,
                    max_retries=3
                )
        
        # Verify exponential backoff pattern (1s, 2s, 4s)
        assert len(sleep_delays) >= 2
        # First retry delay should be ~1s
        assert sleep_delays[0] == 1
        # Second retry delay should be ~2s (doubled)
        assert sleep_delays[1] == 2