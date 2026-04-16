"""Agent Fail Controller for 5-layer fallback strategy.

Implements multi-layer failure recovery per P1 requirements:
- Layer 1: Retry (1 time for retryable errors)
- Layer 2: Alternative tool with attempted_tools check
- Layer 3: Skip step (check total_steps from context)
- Layer 4: Fallback to RAG
- Layer 5: Return partial result

Key improvements from existing agent_runner error recovery:
1. Single retry (not 3 retries) - faster recovery
2. Dynamic total_steps from context (not fixed MAX_STEPS=3)
3. attempted_tools set prevents fallback loops

Usage:
    controller = AgentFailController()
    fail_context = FailContext(
        tool_name="external_search",
        error="timeout",
        current_step=2,
        total_steps=5,
        attempted_tools=set()
    )
    result = await controller.handle_failure(fail_context)
"""

from enum import Enum
from typing import Optional, Set
from dataclasses import dataclass, field

from app.utils.logger import logger


# Error classification constants
RETRYABLE_ERRORS = ["timeout", "network", "unavailable", "temporarily", "connection"]
NON_RETRYABLE_ERRORS = [
    "not found",
    "permission denied",
    "invalid",
    "does not exist",
    "unauthorized",
]

# Tool fallback mappings
ALTERNATIVE_TOOLS = {
    "external_search": "rag_search",
    "rag_search": "external_search",
    "read_paper": "list_papers",
}


class FailAction(Enum):
    """Failure recovery actions ordered by layer (1-5).

    Layer 1: RETRY - Retry once for transient errors
    Layer 2: ALTERNATIVE - Try alternative tool
    Layer 3: SKIP_STEP - Skip current step, continue execution
    Layer 4: FALLBACK_RAG - Fallback to RAG search
    Layer 5: PARTIAL_RESULT - Return partial result with error
    """

    RETRY = "retry"
    ALTERNATIVE = "alternative"
    SKIP_STEP = "skip_step"
    FALLBACK_RAG = "fallback_rag"
    PARTIAL_RESULT = "partial_result"


@dataclass
class FailContext:
    """Context for failure handling.

    Attributes:
        tool_name: Name of the failed tool
        error: Error message from tool execution
        current_step: Current execution step number
        total_steps: Total steps for the plan (from context, can be None)
        attempted_tools: Set of tools already attempted (prevents loops)
        retry_count: Number of retries already attempted (default: 0)
    """

    tool_name: str
    error: str
    current_step: int
    total_steps: Optional[int]
    attempted_tools: Set[str]
    retry_count: int = 0


@dataclass
class FailResult:
    """Result of failure handling.

    Attributes:
        action: Selected recovery action
        alternative_tool: (if ALTERNATIVE) Alternative tool name
        retry_count: Updated retry count
        updated_attempted_tools: Updated set of attempted tools
        message: Human-readable message explaining the action
        should_continue: Whether execution should continue
    """

    action: FailAction
    alternative_tool: Optional[str] = None
    retry_count: int = 0
    updated_attempted_tools: Set[str] = field(default_factory=set)
    message: str = ""
    should_continue: bool = True


class AgentFailController:
    """Controller for multi-layer failure recovery.

    Implements 5-layer fallback strategy:
    1. Retry (1 time) - only for retryable errors
    2. Alternative tool - check attempted_tools to prevent loops
    3. Skip step - if not at last step
    4. Fallback to RAG - final fallback for search failures
    5. Return partial result - when all recovery options exhausted

    Attributes:
        max_retries: Maximum retry attempts (default: 1, per P1)
        default_total_steps: Default total steps when not provided (default: 3)
    """

    def __init__(self, max_retries: int = 1, default_total_steps: int = 3):
        """Initialize AgentFailController.

        Args:
            max_retries: Maximum retry attempts (default: 1)
            default_total_steps: Default total steps when not in context (default: 3)
        """
        self.max_retries = max_retries
        self.default_total_steps = default_total_steps

    def is_retryable_error(self, error: str) -> bool:
        """Check if error is transient and can be retried.

        Args:
            error: Error message string

        Returns:
            True if error is retryable, False otherwise
        """
        error_lower = error.lower()

        # Check for non-retryable errors first
        for non_retryable in NON_RETRYABLE_ERRORS:
            if non_retryable in error_lower:
                return False

        # Check for retryable errors
        for retryable in RETRYABLE_ERRORS:
            if retryable in error_lower:
                return True

        # Default: not retryable
        return False

    def get_alternative_tool(self, failed_tool: str) -> Optional[str]:
        """Get alternative tool for fallback.

        Args:
            failed_tool: Name of the tool that failed

        Returns:
            Alternative tool name, or None if no mapping exists
        """
        return ALTERNATIVE_TOOLS.get(failed_tool)

    def _get_effective_total_steps(self, total_steps: Optional[int]) -> int:
        """Get effective total steps (from context or default).

        Args:
            total_steps: Total steps from context (can be None)

        Returns:
            Effective total steps to use
        """
        return total_steps if total_steps is not None else self.default_total_steps

    def _is_last_step(self, current_step: int, total_steps: Optional[int]) -> bool:
        """Check if current step is the last step.

        Args:
            current_step: Current step number
            total_steps: Total steps from context

        Returns:
            True if current step is the last step
        """
        effective_total = self._get_effective_total_steps(total_steps)
        return current_step >= effective_total

    async def handle_failure(self, context: FailContext) -> FailResult:
        """Handle tool failure with 5-layer fallback strategy.

        Args:
            context: Failure context with tool name, error, step info

        Returns:
            FailResult with selected action and updated state
        """
        logger.info(
            "Handling tool failure",
            tool=context.tool_name,
            error=context.error,
            current_step=context.current_step,
            total_steps=context.total_steps,
            attempted_tools=list(context.attempted_tools),
            retry_count=context.retry_count,
        )

        # Layer 1: Retry (only if retryable and not exceeded max retries)
        if self.is_retryable_error(context.error) and context.retry_count < self.max_retries:
            logger.info(
                "Layer 1: Retry triggered",
                tool=context.tool_name,
                retry_count=context.retry_count + 1,
            )

            updated_attempted = context.attempted_tools.copy()
            updated_attempted.add(context.tool_name)

            return FailResult(
                action=FailAction.RETRY,
                retry_count=context.retry_count + 1,
                updated_attempted_tools=updated_attempted,
                message=f"Retrying {context.tool_name} due to transient error: {context.error}",
                should_continue=True,
            )

        # Layer 2: Alternative tool (if available and not already attempted)
        alternative_tool = self.get_alternative_tool(context.tool_name)
        if alternative_tool and alternative_tool not in context.attempted_tools:
            logger.info(
                "Layer 2: Alternative tool selected",
                primary_tool=context.tool_name,
                alternative_tool=alternative_tool,
            )

            updated_attempted = context.attempted_tools.copy()
            updated_attempted.add(context.tool_name)
            updated_attempted.add(alternative_tool)

            return FailResult(
                action=FailAction.ALTERNATIVE,
                alternative_tool=alternative_tool,
                retry_count=0,  # Reset retry count for alternative
                updated_attempted_tools=updated_attempted,
                message=f"Using alternative tool {alternative_tool} instead of {context.tool_name}",
                should_continue=True,
            )

        # Layer 3: Skip step (if not at last step)
        if not self._is_last_step(context.current_step, context.total_steps):
            logger.info(
                "Layer 3: Skip step",
                current_step=context.current_step,
                total_steps=self._get_effective_total_steps(context.total_steps),
            )

            updated_attempted = context.attempted_tools.copy()
            updated_attempted.add(context.tool_name)

            return FailResult(
                action=FailAction.SKIP_STEP,
                updated_attempted_tools=updated_attempted,
                message=f"Skipping step {context.current_step} due to failure, continuing to next step",
                should_continue=True,
            )

        # Layer 4: Fallback to RAG (for search-related failures)
        if context.tool_name in ["external_search", "rag_search"]:
            logger.info(
                "Layer 4: Fallback to RAG",
                tool=context.tool_name,
            )

            updated_attempted = context.attempted_tools.copy()
            updated_attempted.add(context.tool_name)
            updated_attempted.add("rag_fallback")

            return FailResult(
                action=FailAction.FALLBACK_RAG,
                updated_attempted_tools=updated_attempted,
                message="Falling back to RAG search as final recovery attempt",
                should_continue=True,
            )

        # Layer 5: Return partial result (all recovery options exhausted)
        logger.warning(
            "Layer 5: Return partial result",
            tool=context.tool_name,
            error=context.error,
            all_options_exhausted=True,
        )

        updated_attempted = context.attempted_tools.copy()
        updated_attempted.add(context.tool_name)

        return FailResult(
            action=FailAction.PARTIAL_RESULT,
            updated_attempted_tools=updated_attempted,
            message=f"All recovery options exhausted. Returning partial result with error: {context.error}",
            should_continue=False,
        )