"""Unit tests for AgentFailController.

Tests 5-layer fallback strategy:
- Layer 1: Retry (1 time for retryable errors)
- Layer 2: Alternative tool with attempted_tools check
- Layer 3: Skip step (check total_steps from context)
- Layer 4: Fallback to RAG
- Layer 5: Return partial result

Implements P1 requirements:
- Dynamic total_steps from context (not fixed MAX_STEPS=3)
- attempted_tools set to prevent fallback loops
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from app.core.agent_fail_controller import (
    AgentFailController,
    FailAction,
    FailContext,
)


class TestAgentFailControllerRetryable:
    """Test retryable error detection."""

    def test_timeout_is_retryable(self):
        """Timeout errors should be retryable."""
        controller = AgentFailController()
        assert controller.is_retryable_error("timeout while connecting to server")
        assert controller.is_retryable_error("request timeout")

    def test_network_is_retryable(self):
        """Network errors should be retryable."""
        controller = AgentFailController()
        assert controller.is_retryable_error("network error: connection refused")
        assert controller.is_retryable_error("network unavailable")

    def test_unavailable_is_retryable(self):
        """Service unavailable errors should be retryable."""
        controller = AgentFailController()
        assert controller.is_retryable_error("service unavailable")
        assert controller.is_retryable_error("temporarily unavailable")

    def test_connection_is_retryable(self):
        """Connection errors should be retryable."""
        controller = AgentFailController()
        assert controller.is_retryable_error("connection refused")
        assert controller.is_retryable_error("connection timeout")

    def test_not_found_not_retryable(self):
        """Not found errors should NOT be retryable."""
        controller = AgentFailController()
        assert not controller.is_retryable_error("paper not found")
        assert not controller.is_retryable_error("resource not found")

    def test_permission_denied_not_retryable(self):
        """Permission denied errors should NOT be retryable."""
        controller = AgentFailController()
        assert not controller.is_retryable_error("permission denied")
        assert not controller.is_retryable_error("unauthorized access")

    def test_invalid_not_retryable(self):
        """Invalid parameter errors should NOT be retryable."""
        controller = AgentFailController()
        assert not controller.is_retryable_error("invalid parameter")
        assert not controller.is_retryable_error("invalid request")

    def test_does_not_exist_not_retryable(self):
        """Does not exist errors should NOT be retryable."""
        controller = AgentFailController()
        assert not controller.is_retryable_error("paper does not exist")
        assert not controller.is_retryable_error("user does not exist")


class TestAgentFailControllerFallback:
    """Test fallback logic with dynamic total_steps."""

    @pytest.mark.asyncio
    async def test_total_steps_from_context(self):
        """Fallback should respect total_steps from context."""
        controller = AgentFailController()

        # Create fail context with total_steps=5
        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=3,
            total_steps=5,
            attempted_tools=set(),
        )

        result = await controller.handle_failure(fail_context)

        # At step 3 of 5, should allow skip step (not last step)
        assert result.action in [FailAction.RETRY, FailAction.ALTERNATIVE, FailAction.SKIP_STEP]

    @pytest.mark.asyncio
    async def test_last_step_no_skip(self):
        """At last step with retry exhausted, should NOT skip and should fallback to RAG."""
        controller = AgentFailController()

        # Create fail context at last step with retry already exhausted
        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=5,
            total_steps=5,
            attempted_tools=set(),
            retry_count=1,  # Already retried once (Layer 1 exhausted)
        )

        result = await controller.handle_failure(fail_context)

        # At last step (step 5 of 5), cannot skip - should fallback to RAG
        # Layer 2 (alternative) should also work since rag_search not in attempted_tools
        assert result.action in [FailAction.ALTERNATIVE, FailAction.FALLBACK_RAG, FailAction.PARTIAL_RESULT]

    @pytest.mark.asyncio
    async def test_no_total_steps_default_3(self):
        """Without total_steps in context, should default to 3."""
        controller = AgentFailController()

        # Create fail context without total_steps
        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=2,
            total_steps=None,  # No total_steps provided
            attempted_tools=set(),
        )

        result = await controller.handle_failure(fail_context)

        # Default total_steps=3, at step 2, should allow skip
        assert result.action in [FailAction.RETRY, FailAction.ALTERNATIVE, FailAction.SKIP_STEP]

    @pytest.mark.asyncio
    async def test_step_equals_default_total_steps(self):
        """At step 3 with default total_steps=3 and retry exhausted, should fallback to RAG."""
        controller = AgentFailController()

        # Create fail context at step 3 (default max) with retry exhausted
        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=3,
            total_steps=None,  # Default to 3
            attempted_tools=set(),
            retry_count=1,  # Already retried once
        )

        result = await controller.handle_failure(fail_context)

        # At step 3 of default 3, should try alternative or fallback to RAG or partial result
        assert result.action in [FailAction.ALTERNATIVE, FailAction.FALLBACK_RAG, FailAction.PARTIAL_RESULT]


class TestAgentFailControllerLoopPrevention:
    """Test attempted_tools loop prevention per P1."""

    @pytest.mark.asyncio
    async def test_attempted_tool_not_used_again(self):
        """Tools in attempted_tools should NOT be used as alternatives."""
        controller = AgentFailController()

        # Create fail context with rag_search already attempted
        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=2,
            total_steps=5,
            attempted_tools={"rag_search"},  # rag_search already tried
        )

        result = await controller.handle_failure(fail_context)

        # Should NOT suggest rag_search as alternative (it's in attempted_tools)
        if result.action == FailAction.ALTERNATIVE:
            assert result.alternative_tool != "rag_search"

    @pytest.mark.asyncio
    async def test_alternative_added_to_attempted(self):
        """When alternative tool is used, it should be added to attempted_tools."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=2,
            total_steps=5,
            attempted_tools=set(),
        )

        result = await controller.handle_failure(fail_context)

        # If alternative is suggested, verify it's tracked
        if result.action == FailAction.ALTERNATIVE:
            assert result.alternative_tool in result.updated_attempted_tools

    @pytest.mark.asyncio
    async def test_prevent_rag_external_loop(self):
        """Should prevent rag_search <-> external_search infinite loop."""
        controller = AgentFailController()

        # Simulate the loop scenario after retry exhausted:
        # 1. external_search failed -> tried rag_search
        # 2. rag_search failed -> trying external_search again?
        fail_context = FailContext(
            tool_name="rag_search",
            error="timeout",
            current_step=3,
            total_steps=5,
            attempted_tools={"external_search"},  # external_search already tried
            retry_count=1,  # Already retried once
        )

        result = await controller.handle_failure(fail_context)

        # Should NOT suggest external_search as alternative (prevents loop)
        if result.action == FailAction.ALTERNATIVE:
            assert result.alternative_tool != "external_search"

        # Should move to skip or fallback instead
        assert result.action in [FailAction.SKIP_STEP, FailAction.FALLBACK_RAG, FailAction.PARTIAL_RESULT]


class TestAgentFailControllerBasic:
    """Test basic retry and fallback behavior."""

    @pytest.mark.asyncio
    async def test_retry_triggered_once(self):
        """Retry should be triggered exactly once for retryable errors."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",  # Retryable error
            current_step=1,
            total_steps=5,
            attempted_tools=set(),
        )

        result = await controller.handle_failure(fail_context)

        # First failure with retryable error should trigger retry
        assert result.action == FailAction.RETRY
        assert result.retry_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_after_max(self):
        """After max retries (1), should NOT retry again."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=1,
            total_steps=5,
            attempted_tools=set(),
            retry_count=1,  # Already retried once
        )

        result = await controller.handle_failure(fail_context)

        # After max retry, should NOT retry again
        assert result.action != FailAction.RETRY

    @pytest.mark.asyncio
    async def test_non_retryable_no_retry(self):
        """Non-retryable errors should NOT trigger retry."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="read_paper",
            error="paper not found",  # Non-retryable error
            current_step=1,
            total_steps=5,
            attempted_tools=set(),
        )

        result = await controller.handle_failure(fail_context)

        # Non-retryable error should skip retry layer
        assert result.action != FailAction.RETRY

    @pytest.mark.asyncio
    async def test_alternative_tool_mapping(self):
        """Should correctly map alternative tools."""
        controller = AgentFailController()

        # external_search -> rag_search
        alt = controller.get_alternative_tool("external_search")
        assert alt == "rag_search"

        # rag_search -> external_search
        alt = controller.get_alternative_tool("rag_search")
        assert alt == "external_search"

        # read_paper -> list_papers
        alt = controller.get_alternative_tool("read_paper")
        assert alt == "list_papers"

    @pytest.mark.asyncio
    async def test_alternative_excluded_if_attempted(self):
        """Alternative tool should be excluded if already attempted."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=2,
            total_steps=5,
            attempted_tools={"rag_search"},  # Alternative already tried
            retry_count=1,  # Already retried once (Layer 1 exhausted)
        )

        result = await controller.handle_failure(fail_context)

        # Should skip alternative layer since rag_search is already attempted
        assert result.action in [FailAction.SKIP_STEP, FailAction.FALLBACK_RAG, FailAction.PARTIAL_RESULT]

    @pytest.mark.asyncio
    async def test_fallback_rag_when_no_alternative(self):
        """Should fallback to RAG when no alternative available and retry exhausted."""
        controller = AgentFailController()

        fail_context = FailContext(
            tool_name="unknown_tool",  # No alternative mapping
            error="timeout",
            current_step=2,
            total_steps=5,
            attempted_tools=set(),
            retry_count=1,  # Already retried once (Layer 1 exhausted)
        )

        result = await controller.handle_failure(fail_context)

        # No alternative for unknown_tool -> should skip step or fallback to RAG
        assert result.action in [FailAction.SKIP_STEP, FailAction.FALLBACK_RAG, FailAction.PARTIAL_RESULT]


class TestFailActionEnum:
    """Test FailAction enum values."""

    def test_fail_action_values(self):
        """FailAction should have all 5 layers."""
        assert FailAction.RETRY.value == "retry"
        assert FailAction.ALTERNATIVE.value == "alternative"
        assert FailAction.SKIP_STEP.value == "skip_step"
        assert FailAction.FALLBACK_RAG.value == "fallback_rag"
        assert FailAction.PARTIAL_RESULT.value == "partial_result"

    def test_fail_action_order(self):
        """FailAction should be ordered from Layer 1 to Layer 5."""
        actions = list(FailAction)
        assert actions[0] == FailAction.RETRY
        assert actions[1] == FailAction.ALTERNATIVE
        assert actions[2] == FailAction.SKIP_STEP
        assert actions[3] == FailAction.FALLBACK_RAG
        assert actions[4] == FailAction.PARTIAL_RESULT


class TestFailContext:
    """Test FailContext dataclass."""

    def test_fail_context_creation(self):
        """FailContext should be created with all fields."""
        context = FailContext(
            tool_name="external_search",
            error="timeout",
            current_step=2,
            total_steps=5,
            attempted_tools={"rag_search"},
            retry_count=1,
        )

        assert context.tool_name == "external_search"
        assert context.error == "timeout"
        assert context.current_step == 2
        assert context.total_steps == 5
        assert "rag_search" in context.attempted_tools
        assert context.retry_count == 1

    def test_fail_context_default_values(self):
        """FailContext should have correct default values."""
        context = FailContext(
            tool_name="test_tool",
            error="test error",
            current_step=1,
            total_steps=3,
            attempted_tools=set(),
        )

        assert context.retry_count == 0  # Default
        assert context.total_steps == 3

    def test_fail_context_attempted_tools_mutable(self):
        """FailContext attempted_tools should be mutable set."""
        context = FailContext(
            tool_name="test",
            error="test",
            current_step=1,
            total_steps=3,
            attempted_tools=set(),
        )

        context.attempted_tools.add("tool1")
        assert "tool1" in context.attempted_tools