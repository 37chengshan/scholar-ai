"""Unit tests for Agent UI State mapping.

Tests 4-state UI model per D-04:
- IDLE: Ready for input
- RUNNING: Executing (THINKING + TOOL_SELECTION + TOOL_EXECUTION + VERIFYING)
- WAITING: Awaiting user confirmation (WAITING_CONFIRMATION)
- DONE: Completed (COMPLETED + FAILED with success flag)

Test Coverage:
- UI state mapping for all 8 internal states
- get_ui_state() method on AgentRunner
- State transitions preserve internal states for logging
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.agent_runner import AgentRunner, AgentState


class TestAgentUIState:
    """Test AgentUIState enum and to_ui_state() mapping."""

    def test_agent_ui_state_enum_exists(self):
        """Test that AgentUIState enum is defined with 4 states."""
        from app.core.agent_runner import AgentUIState

        assert hasattr(AgentUIState, "IDLE")
        assert hasattr(AgentUIState, "RUNNING")
        assert hasattr(AgentUIState, "WAITING")
        assert hasattr(AgentUIState, "DONE")

    def test_ui_state_mapping_idle(self):
        """Test IDLE state maps correctly."""
        from app.core.agent_runner import AgentUIState

        # IDLE → IDLE
        result = AgentState.IDLE.to_ui_state()
        assert result.state == AgentUIState.IDLE
        # PAUSED → IDLE
        result = AgentState.PAUSED.to_ui_state()
        assert result.state == AgentUIState.IDLE

    def test_ui_state_mapping_running(self):
        """Test RUNNING state maps from multiple internal states."""
        from app.core.agent_runner import AgentUIState

        # THINKING → RUNNING
        result = AgentState.THINKING.to_ui_state()
        assert result.state == AgentUIState.RUNNING
        # TOOL_SELECTION → RUNNING
        result = AgentState.TOOL_SELECTION.to_ui_state()
        assert result.state == AgentUIState.RUNNING
        # TOOL_EXECUTION → RUNNING
        result = AgentState.TOOL_EXECUTION.to_ui_state()
        assert result.state == AgentUIState.RUNNING
        # VERIFYING → RUNNING
        result = AgentState.VERIFYING.to_ui_state()
        assert result.state == AgentUIState.RUNNING

    def test_ui_state_mapping_waiting(self):
        """Test WAITING state maps from WAITING_CONFIRMATION."""
        from app.core.agent_runner import AgentUIState

        # WAITING_CONFIRMATION → WAITING
        result = AgentState.WAITING_CONFIRMATION.to_ui_state()
        assert result.state == AgentUIState.WAITING

    def test_ui_state_mapping_done(self):
        """Test DONE state maps from COMPLETED and FAILED."""
        from app.core.agent_runner import AgentUIState, DoneState

        # COMPLETED → DONE with success=True
        result = AgentState.COMPLETED.to_ui_state()
        assert result.state == AgentUIState.DONE
        assert result.success is True

        # FAILED → DONE with success=False
        result = AgentState.FAILED.to_ui_state()
        assert result.state == AgentUIState.DONE
        assert result.success is False


class TestAgentRunnerGetUIState:
    """Test get_ui_state() method on AgentRunner."""

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

    def test_get_ui_state_returns_current_ui_state(self, agent_runner):
        """Test get_ui_state() returns UI state based on current internal state."""
        from app.core.agent_runner import AgentUIState

        # Initially IDLE
        agent_runner.current_state = AgentState.IDLE
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.IDLE

        # During THINKING
        agent_runner.current_state = AgentState.THINKING
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.RUNNING

        # Waiting for confirmation
        agent_runner.current_state = AgentState.WAITING_CONFIRMATION
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.WAITING

        # Completed
        agent_runner.current_state = AgentState.COMPLETED
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.DONE
        assert ui_state.success is True

        # Failed
        agent_runner.current_state = AgentState.FAILED
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.DONE
        assert ui_state.success is False

    def test_internal_states_preserved_for_logging(self, agent_runner):
        """Test that internal states are still tracked while exposing simplified states."""
        from app.core.agent_runner import AgentUIState

        # Agent should track internal state separately
        agent_runner.current_state = AgentState.THINKING

        # get_ui_state() should return simplified state
        ui_state = agent_runner.get_ui_state()
        assert ui_state.state == AgentUIState.RUNNING

        # But internal state should still be THINKING
        assert agent_runner.current_state == AgentState.THINKING


class TestDoneStateDataclass:
    """Test DoneState dataclass for DONE state with success flag."""

    def test_done_state_has_success_flag(self):
        """Test DoneState includes success flag to distinguish COMPLETED from FAILED."""
        from app.core.agent_runner import DoneState, AgentUIState

        # Success case
        done_success = DoneState(state=AgentUIState.DONE, success=True)
        assert done_success.state == AgentUIState.DONE
        assert done_success.success is True

        # Failure case
        done_failure = DoneState(state=AgentUIState.DONE, success=False)
        assert done_failure.state == AgentUIState.DONE
        assert done_failure.success is False
