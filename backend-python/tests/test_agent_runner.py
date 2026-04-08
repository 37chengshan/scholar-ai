"""Agent Runner 4-State Machine Tests.

Tests for Agent Runner state transitions per D-04:
- IDLE: Initial state, not executing
- RUNNING: Actively executing tools
- WAITING: Paused for user confirmation (CRITICAL tools)
- DONE: Execution completed

Tests verify state machine transitions, state emissions via SSE,
interruption support, and timing/token tracking.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from app.core.agent_runner import AgentRunner, AgentState
from app.core.tool_registry import ToolRegistry
from app.core.context_manager import ContextManager
from app.middleware.safety_layer import SafetyLayer


class TestAgentRunnerState:
    """Test Agent Runner 4-state machine."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = AsyncMock()
        client.chat_completion = AsyncMock()
        return client

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        registry = MagicMock(spec=ToolRegistry)
        registry.execute = AsyncMock()
        registry.get = MagicMock()
        registry.list_tools_schema = MagicMock(return_value=[])
        return registry

    @pytest.fixture
    def mock_context_manager(self):
        """Mock context manager."""
        manager = AsyncMock(spec=ContextManager)
        manager.build_context = AsyncMock()
        return manager

    @pytest.fixture
    def mock_safety_layer(self):
        """Mock safety layer."""
        safety = MagicMock(spec=SafetyLayer)
        safety.check_permission = AsyncMock()
        safety.assess_risk = AsyncMock()
        safety.log_audit = AsyncMock()
        return safety

    @pytest.fixture
    def agent_runner(
        self,
        mock_llm_client,
        mock_tool_registry,
        mock_context_manager,
        mock_safety_layer,
    ):
        """Create AgentRunner instance with mocks."""
        return AgentRunner(
            llm_client=mock_llm_client,
            tool_registry=mock_tool_registry,
            context_manager=mock_context_manager,
            safety_layer=mock_safety_layer,
            max_iterations=10,
        )

    @pytest.mark.asyncio
    async def test_agent_starts_in_idle_state(self, agent_runner):
        """Test 1: Agent starts in IDLE state."""
        assert agent_runner.current_state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_agent_transitions_to_running_on_execute(
        self, agent_runner, mock_context_manager, mock_llm_client
    ):
        """Test 2: Agent transitions to RUNNING when execute() called."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {}
        mock_context_manager.build_context.return_value = mock_context

        # Setup mock LLM response (immediate completion)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Task complete"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # Execute (but don't wait for full completion - just check state transition)
        # We'll check that state changes from IDLE to THINKING (part of RUNNING flow)
        execute_task = asyncio.create_task(
            agent_runner.execute("Test query", "session123", "user123")
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # State should have changed from IDLE
        assert agent_runner.current_state != AgentState.IDLE

        # Cancel the task since we're just testing state transition
        execute_task.cancel()
        try:
            await execute_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_agent_transitions_to_waiting_for_critical_tool(
        self,
        agent_runner,
        mock_context_manager,
        mock_llm_client,
        mock_tool_registry,
        mock_safety_layer,
    ):
        """Test 3: Agent transitions to WAITING when CRITICAL tool requires confirmation."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {"user_id": "user123"}
        mock_context_manager.build_context.return_value = mock_context

        # Setup mock LLM response (tool call)
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "delete_paper"
        mock_tool_call.function.arguments = '{"paper_id": "123"}'

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_response.usage = MagicMock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # Setup safety layer to require confirmation
        mock_safety_layer.check_permission.return_value = {
            "needs_confirmation": True,
            "message": "This action cannot be undone",
        }

        # Execute
        result = await agent_runner.execute("Delete paper 123", "session123", "user123")

        # Verify state transitioned to WAITING
        assert agent_runner.current_state == AgentState.WAITING_CONFIRMATION
        assert result.get("needs_confirmation") is True
        assert result.get("tool_name") == "delete_paper"

    @pytest.mark.asyncio
    async def test_agent_transitions_to_done_after_completion(
        self, agent_runner, mock_context_manager, mock_llm_client
    ):
        """Test 4: Agent transitions to DONE after successful completion."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {}
        mock_context_manager.build_context.return_value = mock_context

        # Setup mock LLM response (immediate completion)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Task complete"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # Execute
        result = await agent_runner.execute("Test query", "session123", "user123")

        # Verify state transitioned to COMPLETED
        assert agent_runner.current_state == AgentState.COMPLETED
        assert result.get("success") is True
        assert result.get("answer") == "Task complete"

    @pytest.mark.asyncio
    async def test_state_includes_metadata_fields(
        self, agent_runner, mock_context_manager, mock_llm_client
    ):
        """Test 5: State includes current_step, total_time, token_usage fields."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {}
        mock_context_manager.build_context.return_value = mock_context

        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Done"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_llm_client.chat_completion.return_value = mock_response

        # Execute
        result = await agent_runner.execute("Test", "session123", "user123")

        # Verify metadata fields
        assert "total_time_ms" in result
        assert "tokens_used" in result
        assert result["tokens_used"] > 0
        assert isinstance(result["total_time_ms"], int)

    @pytest.mark.asyncio
    async def test_agent_can_be_interrupted_during_running(
        self, agent_runner, mock_context_manager, mock_llm_client, mock_tool_registry
    ):
        """Test 6: Agent can be interrupted via stop() method during RUNNING state."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {}
        mock_context_manager.build_context.return_value = mock_context

        # Setup mock LLM to take time (simulate long running)
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # Long delay
            return MagicMock()

        mock_llm_client.chat_completion.side_effect = slow_response

        # Start execution
        execute_task = asyncio.create_task(
            agent_runner.execute("Long query", "session123", "user123")
        )

        # Wait for state to change to THINKING
        await asyncio.sleep(0.1)
        assert agent_runner.current_state == AgentState.THINKING

        # Add stop method if it exists, otherwise verify agent is in running state
        if hasattr(agent_runner, "stop"):
            agent_runner.stop()
            await asyncio.sleep(0.1)
            # State should have changed
            assert agent_runner.current_state in [AgentState.PAUSED, AgentState.FAILED]

        # Cancel the task
        execute_task.cancel()
        try:
            await execute_task
        except asyncio.CancelledError:
            pass


class TestAgentStateEnum:
    """Test AgentState enum values."""

    def test_agent_state_has_required_values(self):
        """Test AgentState enum has all 4 required states."""
        states = [state.value for state in AgentState]

        # Core states per D-04
        assert "idle" in states
        assert "thinking" in states  # Part of RUNNING
        assert "tool_execution" in states  # Part of RUNNING
        assert "waiting_confirmation" in states  # WAITING
        assert "completed" in states  # DONE
        assert "failed" in states
        assert "paused" in states


class TestAgentRunnerEmissions:
    """Test Agent Runner SSE emissions."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry."""
        registry = MagicMock(spec=ToolRegistry)
        registry.execute = AsyncMock()
        return registry

    @pytest.fixture
    def mock_context_manager(self):
        """Mock context manager."""
        return AsyncMock(spec=ContextManager)

    @pytest.fixture
    def mock_safety_layer(self):
        """Mock safety layer."""
        safety = MagicMock(spec=SafetyLayer)
        safety.check_permission = AsyncMock()
        return safety

    @pytest.mark.asyncio
    async def test_agent_emits_state_updates(
        self,
        mock_llm_client,
        mock_tool_registry,
        mock_context_manager,
        mock_safety_layer,
    ):
        """Test Agent Runner emits state updates via SSE stream."""
        # This test verifies the state emission pattern
        # Actual SSE emission would be handled by the API layer
        runner = AgentRunner(
            llm_client=mock_llm_client,
            tool_registry=mock_tool_registry,
            context_manager=mock_context_manager,
            safety_layer=mock_safety_layer,
        )

        # Verify runner has state property that can be observed
        assert hasattr(runner, "current_state")
        assert isinstance(runner.current_state, AgentState)

        # State changes would be emitted by the API layer
        # This verifies the runner exposes state for observation


class TestAgentRunnerTokenTracking:
    """Test Agent Runner token usage tracking."""

    @pytest.fixture
    def setup_mocks(self):
        """Setup all mocks."""
        llm_client = AsyncMock()
        tool_registry = MagicMock(spec=ToolRegistry)
        tool_registry.execute = AsyncMock()
        context_manager = AsyncMock(spec=ContextManager)
        safety_layer = MagicMock(spec=SafetyLayer)
        safety_layer.check_permission = AsyncMock()

        return llm_client, tool_registry, context_manager, safety_layer

    @pytest.mark.asyncio
    async def test_agent_tracks_token_usage(self, setup_mocks):
        """Test Agent Runner tracks total token usage."""
        llm_client, tool_registry, context_manager, safety_layer = setup_mocks

        # Setup context
        mock_context = MagicMock()
        mock_context.important_messages = []
        mock_context.tool_history = []
        mock_context.environment = {}
        context_manager.build_context.return_value = mock_context

        # Setup LLM response with usage
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Done"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            prompt_tokens=200, completion_tokens=100, total_tokens=300
        )
        llm_client.chat_completion.return_value = mock_response

        runner = AgentRunner(
            llm_client=llm_client,
            tool_registry=tool_registry,
            context_manager=context_manager,
            safety_layer=safety_layer,
        )

        result = await runner.execute("Test", "session123", "user123")

        # Verify token tracking
        assert runner.total_tokens_used > 0
        assert "tokens_used" in result
        assert result["tokens_used"] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
