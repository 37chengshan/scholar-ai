"""Agent Runner execution engine.

Implements D-05 from Agent-Native architecture:
ReAct (Reasoning + Acting) pattern for multi-step agent execution.

Implements D-11 from Phase 22:
Enhanced system prompt with reasoning framework.

Implements D-12 from Phase 22:
Multi-layer error recovery (retry → alternative → user decision).

Agent Execution Flow:
1. Build context from session
2. THINKING: Call LLM to determine next action
3. TOOL_SELECTION: Extract tool call from LLM response
4. Check permission via Safety Layer
5. TOOL_EXECUTION: Execute tool with parameters (with error recovery)
6. Update context and loop until complete
7. Return final answer

Usage:
    runner = AgentRunner(llm_client, registry, context_mgr, safety)
    result = await runner.execute("Find papers about AI", session_id, user_id)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import asyncio
import time

from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager, Context
from app.core.config import settings
from app.utils.logger import logger
from app.utils.zhipu_client import get_llm_client
from app.utils.token_tracker import TokenTracker


# Error recovery constants per D-12
RETRYABLE_ERRORS = ["timeout", "network", "unavailable", "connection", "temporarily"]
NON_RETRYABLE_ERRORS = [
    "not found",
    "permission denied",
    "invalid",
    "required",
    "does not exist",
    "unauthorized",
]

# Alternative tool mappings for fallback per D-12
ALTERNATIVE_TOOLS = {
    "external_search": "rag_search",  # External search failed -> try RAG search
    "rag_search": "external_search",  # RAG search failed -> try external search
}


class AgentState(Enum):
    """Agent execution states.

    States represent the agent's current phase in the execution loop.
    """

    IDLE = "idle"  # Not executing
    THINKING = "thinking"  # Calling LLM to decide action
    TOOL_SELECTION = "tool_selection"  # Parsing tool call from response
    TOOL_EXECUTION = "tool_execution"  # Executing selected tool
    WAITING_CONFIRMATION = "waiting_confirmation"  # Paused for user confirmation
    VERIFYING = "verifying"  # Verifying tool result
    COMPLETED = "completed"  # Task complete, returning answer
    FAILED = "failed"  # Execution failed
    PAUSED = "paused"  # Paused by user

    def to_ui_state(self) -> "UIStateResult":
        """Map internal state to simplified 4-state UI model.

        Per D-04: Coarse-grained 4-state machine for UI:
        - IDLE: Ready for input
        - RUNNING: Executing (THINKING, TOOL_SELECTION, TOOL_EXECUTION, VERIFYING)
        - WAITING: Awaiting user confirmation (WAITING_CONFIRMATION)
        - DONE: Completed (COMPLETED with success=True, FAILED with success=False)

        Returns:
            UIStateResult (either AgentUIState or DoneState)
        """
        mapping = {
            AgentState.IDLE: AgentUIState.IDLE,
            AgentState.THINKING: AgentUIState.RUNNING,
            AgentState.TOOL_SELECTION: AgentUIState.RUNNING,
            AgentState.TOOL_EXECUTION: AgentUIState.RUNNING,
            AgentState.VERIFYING: AgentUIState.RUNNING,
            AgentState.WAITING_CONFIRMATION: AgentUIState.WAITING,
            AgentState.PAUSED: AgentUIState.IDLE,
        }

        if self == AgentState.COMPLETED:
            return DoneState(state=AgentUIState.DONE, success=True)
        elif self == AgentState.FAILED:
            return DoneState(state=AgentUIState.DONE, success=False)
        else:
            return UIStateResult(state=mapping[self])


class AgentUIState(Enum):
    """Simplified 4-state UI model for frontend display.

    Per D-04: Coarse-grained states for user-friendly display.
    """

    IDLE = "idle"  # Ready for input
    RUNNING = "running"  # Executing
    WAITING = "waiting"  # Awaiting confirmation
    DONE = "done"  # Completed


@dataclass
class UIStateResult:
    """Result container for UI state queries.

    For non-DONE states, wraps AgentUIState.
    """

    state: AgentUIState


@dataclass
class DoneState(UIStateResult):
    """DONE state with success flag to distinguish COMPLETED from FAILED.

    Per D-04: DONE state includes success boolean.
    """

    state: AgentUIState = AgentUIState.DONE
    success: bool = True


class AgentRunner:
    """Agent execution engine with ReAct pattern.

    Implements multi-step reasoning and acting:
    - Call LLM to determine next action (reasoning)
    - Execute tool based on LLM decision (acting)
    - Loop until task complete or max iterations

    Attributes:
        llm_client: LLM client (GLM-4.5-Air)
        tool_registry: Tool registry for tool discovery
        context_manager: Context manager for conversation history
        safety_layer: Safety layer for permission checks
        max_iterations: Maximum execution iterations (default: 10)
        current_state: Current agent state
        iteration_count: Current iteration number
    """

    def __init__(
        self,
        llm_client: Any,
        tool_registry: ToolRegistry,
        context_manager: ContextManager,
        safety_layer: SafetyLayer,
        max_iterations: int = 10,
    ):
        """Initialize Agent Runner.

        Args:
            llm_client: LLM client instance
            tool_registry: Tool registry instance
            context_manager: Context manager instance
            safety_layer: Safety layer instance
            max_iterations: Maximum iterations before stopping
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.safety_layer = safety_layer
        self.max_iterations = max_iterations
        self.current_state = AgentState.IDLE
        self.iteration_count = 0
        self.token_tracker = TokenTracker()
        self.total_tokens_used = 0
        self.total_cost = 0.0

    def get_ui_state(self) -> UIStateResult:
        """Get current UI state based on internal state.

        Per D-04: Returns simplified 4-state model for frontend display.
        Preserves internal state for detailed logging while exposing
        simplified states to UI.

        Returns:
            UIStateResult (either AgentUIState or DoneState with success flag)
        """
        return self.current_state.to_ui_state()

    async def execute(
        self, user_input: str, session_id: str, user_id: str, auto_confirm: bool = False
    ) -> Dict[str, Any]:
        """Execute agent task with ReAct pattern.

        Main execution loop:
        1. Build context from session
        2. Loop until complete or max iterations:
           a. THINKING: Call LLM with tools
           b. Check if complete -> return answer
           c. TOOL_SELECTION: Extract tool call
           d. Check permission via Safety Layer
           e. If needs_confirmation -> pause
           f. TOOL_EXECUTION: Execute tool
           g. Update context
        3. Return result

        Args:
            user_input: User's query or instruction
            session_id: Session ID for context
            user_id: User ID for permission checks
            auto_confirm: Auto-confirm dangerous operations (default: False)

        Returns:
            Dict with:
                - success: Whether execution completed successfully
                - answer: Final answer (if completed)
                - tool_calls: List of tool calls made
                - iterations: Number of iterations used
                - state: Final agent state
                - needs_confirmation: (if paused) confirmation request
        """
        logger.info(
            "Agent execution started",
            user_id=user_id,
            session_id=session_id,
            input=user_input[:100],
        )

        start_time = time.time()
        self.current_state = AgentState.THINKING
        self.iteration_count = 0
        self.total_tokens_used = 0
        self.total_cost = 0.0
        tool_calls_history: List[Dict[str, Any]] = []

        # Build context
        context = await self.context_manager.build_context(session_id)
        context.objective = user_input
        context.environment["user_id"] = user_id

        # System prompt for agent
        system_prompt = self._build_system_prompt(context)

        # Messages for LLM
        messages = self._build_messages(context, user_input)

        # Get tool schemas
        tools_schema = self.tool_registry.list_tools_schema()

        try:
            while self.iteration_count < self.max_iterations:
                self.iteration_count += 1

                logger.info(
                    "Iteration started",
                    iteration=self.iteration_count,
                    state=self.current_state.value,
                )

                # THINKING: Call LLM
                self.current_state = AgentState.THINKING
                llm_response = await self._think(
                    system_prompt, messages, tools_schema, user_id, session_id
                )

                # Check if LLM provided final answer
                if llm_response.get("is_complete", False):
                    self.current_state = AgentState.COMPLETED
                    total_time_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        "Agent completed",
                        iterations=self.iteration_count,
                        answer_length=len(llm_response.get("content", "")),
                        total_tokens=self.total_tokens_used,
                        total_cost=self.total_cost,
                        total_time_ms=total_time_ms,
                    )

                    return {
                        "success": True,
                        "answer": llm_response.get("content"),
                        "tool_calls": tool_calls_history,
                        "iterations": self.iteration_count,
                        "state": self.current_state.value,
                        "tokens_used": self.total_tokens_used,
                        "cost": self.total_cost,
                        "total_time_ms": total_time_ms,
                    }

                # TOOL_SELECTION: Extract tool call
                self.current_state = AgentState.TOOL_SELECTION
                tool_call = llm_response.get("tool_call")

                if not tool_call:
                    # No tool call, but not complete - treat as error
                    logger.error(
                        "No tool call in LLM response", iteration=self.iteration_count
                    )
                    self.current_state = AgentState.FAILED

                    return {
                        "success": False,
                        "error": "LLM did not provide tool call or final answer",
                        "tool_calls": tool_calls_history,
                        "iterations": self.iteration_count,
                        "state": self.current_state.value,
                    }

                tool_name = tool_call.get("name")
                tool_parameters = tool_call.get("parameters", {})

                logger.info("Tool selected", tool=tool_name, parameters=tool_parameters)

                # Check permission
                permission_context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "tool_name": tool_name,
                    "parameters": tool_parameters,
                }

                permission_result = await self.safety_layer.check_permission(
                    tool_name, permission_context
                )

                # If needs confirmation
                if permission_result.get("needs_confirmation", False):
                    if auto_confirm:
                        # Auto-confirm dangerous operations
                        logger.info("Auto-confirming dangerous tool", tool=tool_name)
                    else:
                        # Pause for user confirmation
                        self.current_state = AgentState.WAITING_CONFIRMATION

                        logger.info(
                            "Agent paused for confirmation",
                            tool=tool_name,
                            message=permission_result.get("message"),
                        )

                        return {
                            "success": False,
                            "needs_confirmation": True,
                            "tool_name": tool_name,
                            "tool_parameters": tool_parameters,
                            "message": permission_result.get("message"),
                            "tool_calls": tool_calls_history,
                            "iterations": self.iteration_count,
                            "state": self.current_state.value,
                        }

                # TOOL_EXECUTION: Execute tool with multi-layer error recovery
                self.current_state = AgentState.TOOL_EXECUTION

                tool_result = await self._execute_with_fallback(
                    tool_name, tool_parameters, context
                )

                logger.info(
                    "Tool executed", tool=tool_name, success=tool_result.get("success")
                )

                # Record tool call
                tool_calls_history.append(
                    {
                        "iteration": self.iteration_count,
                        "tool": tool_name,
                        "parameters": tool_parameters,
                        "result": tool_result,
                    }
                )

                # Update context with tool result
                context.tool_history.append(
                    {
                        "tool": tool_name,
                        "parameters": tool_parameters,
                        "result": tool_result,
                    }
                )

                # Add tool result to messages
                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(tool_result),
                        "name": tool_name,
                    }
                )

                # Check if tool execution failed
                if not tool_result.get("success", False):
                    # Handle tool execution error
                    error_msg = tool_result.get("error", "Tool execution failed")

                    logger.error(
                        "Tool execution failed", tool=tool_name, error=error_msg
                    )

                    # Special case: Tool not found - fail immediately (cannot recover)
                    if "not found" in error_msg.lower():
                        self.current_state = AgentState.FAILED

                        return {
                            "success": False,
                            "error": error_msg,
                            "tool_calls": tool_calls_history,
                            "iterations": self.iteration_count,
                            "state": self.current_state.value,
                        }

                    # Other errors: Add error to messages and continue (let LLM decide how to handle)
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Tool '{tool_name}' failed: {error_msg}. I'll try a different approach.",
                        }
                    )

                    # Continue to next iteration
                    continue

            # Max iterations reached
            self.current_state = AgentState.FAILED

            logger.warning("Max iterations reached", iterations=self.iteration_count)

            return {
                "success": False,
                "error": f"Max iterations ({self.max_iterations}) reached without completion",
                "tool_calls": tool_calls_history,
                "iterations": self.iteration_count,
                "state": self.current_state.value,
            }

        except Exception as e:
            self.current_state = AgentState.FAILED

            logger.error(
                "Agent execution failed", error=str(e), iteration=self.iteration_count
            )

            return {
                "success": False,
                "error": str(e),
                "tool_calls": tool_calls_history,
                "iterations": self.iteration_count,
                "state": self.current_state.value,
            }

    async def _think(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: List[Dict[str, Any]],
        user_id: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        """Call LLM to determine next action.

        Args:
            system_prompt: System prompt for agent
            messages: Conversation messages
            tools_schema: Available tool schemas
            user_id: User ID for token tracking
            session_id: Session ID for token tracking

        Returns:
            Dict with:
                - is_complete: Whether LLM provided final answer
                - content: (if complete) Final answer text
                - tool_call: (if not complete) Tool call dict
        """
        try:
            llm_client = get_llm_client()

            # Call LLM with tools
            response = await llm_client.chat_completion(
                messages=[{"role": "system", "content": system_prompt}, *messages],
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.7,
            )

            # Debug: Log raw response structure
            logger.debug(
                "Raw LLM response received",
                response_type=type(response).__name__,
                has_usage=hasattr(response, "usage"),
                usage_type=type(response.usage).__name__
                if hasattr(response, "usage")
                else None,
                usage_repr=str(response.usage) if hasattr(response, "usage") else None,
            )

            # Track token usage - handle different response formats
            if hasattr(response, "usage") and response.usage:
                try:
                    usage_data = response.usage

                    # Handle dict format (some APIs return dict instead of object)
                    if isinstance(usage_data, dict):
                        prompt_tokens = usage_data.get("prompt_tokens", 0)
                        completion_tokens = usage_data.get("completion_tokens", 0)
                        total_tokens = usage_data.get("total_tokens", 0)
                    else:
                        # Handle object format (Pydantic model)
                        prompt_tokens = getattr(usage_data, "prompt_tokens", 0) or 0
                        completion_tokens = (
                            getattr(usage_data, "completion_tokens", 0) or 0
                        )
                        total_tokens = getattr(usage_data, "total_tokens", 0) or 0

                    self.total_tokens_used += total_tokens

                    cost = await self.token_tracker.track_usage(
                        user_id=user_id,
                        model="glm-4.5-air",
                        input_tokens=prompt_tokens,
                        output_tokens=completion_tokens,
                        session_id=session_id,
                    )

                    self.total_cost += cost if cost else 0

                    logger.info(
                        "Token usage tracked",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        accumulated_tokens=self.total_tokens_used,
                        cost_cny=cost,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to track token usage",
                        error=str(e),
                        usage_repr=str(response.usage),
                    )

            # Parse response
            message = response.choices[0].message

            # Check if LLM made a tool call
            if hasattr(message, "tool_calls") and message.tool_calls:
                # Extract first tool call
                tool_call = message.tool_calls[0]

                return {
                    "is_complete": False,
                    "tool_call": {
                        "name": tool_call.function.name,
                        "parameters": json.loads(tool_call.function.arguments),
                    },
                }

            # No tool call - treat as final answer
            content = message.content

            return {"is_complete": True, "content": content}

        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            raise

    async def _execute_tool(
        self, tool_name: str, parameters: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Execute a tool with parameters.

        Args:
            tool_name: Tool to execute
            parameters: Tool parameters
            context: Execution context

        Returns:
            Tool result dict with:
                - success: Whether execution succeeded
                - data: (if success) Tool output
                - error: (if failed) Error message
        """
        tool = self.tool_registry.get(tool_name)

        if not tool:
            logger.error("Tool not found", tool=tool_name)
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry",
            }

        try:
            # Execute tool via Tool Registry (actual implementation)
            logger.info(
                "Executing tool via registry", tool=tool_name, parameters=parameters
            )

            result = await self.tool_registry.execute(
                tool_name, parameters, **context.environment
            )

            logger.info(
                "Tool execution completed",
                tool=tool_name,
                success=result.get("success"),
            )

            return result

        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))

            return {"success": False, "error": str(e)}

    def _is_retryable_error(self, error: str) -> bool:
        """Check if error is transient and can be retried.

        Per D-12: Non-retryable errors are "not found", "permission denied",
        "invalid", "required". Retryable errors are "timeout", "network", "unavailable".

        Args:
            error: Error message string

        Returns:
            True if error is retryable, False otherwise
        """
        error_lower = error.lower()

        # Check for non-retryable errors first (these should NOT be retried)
        for non_retryable in NON_RETRYABLE_ERRORS:
            if non_retryable in error_lower:
                return False

        # Check for retryable errors
        for retryable in RETRYABLE_ERRORS:
            if retryable in error_lower:
                return True

        # Default: not retryable
        return False

    def _get_alternative_tool(self, failed_tool: str) -> Optional[str]:
        """Get alternative tool for fallback when primary fails.

        Per D-12: Provides fallback tools for search operations.

        Args:
            failed_tool: Name of the tool that failed

        Returns:
            Alternative tool name, or None if no alternative exists
        """
        return ALTERNATIVE_TOOLS.get(failed_tool)

    async def _execute_with_fallback(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Context,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Execute tool with multi-layer error recovery.

        Per D-12: Three-layer recovery mechanism:
        1. Auto-retry (3 times with exponential backoff: 1s, 2s, 4s)
        2. Alternative tool (external_search → rag_search fallback)
        3. User decision (explain error, suggest solutions)

        Args:
            tool_name: Primary tool to execute
            params: Tool parameters
            context: Execution context
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Tool result with:
                - success: Whether execution succeeded
                - data: Tool output (if success)
                - error: Error message (if failed)
                - used_alternative: True if alternative tool was used
                - needs_user_decision: True if all recovery options exhausted
        """
        # Layer 1: Retry with exponential backoff
        backoff_delays = [1, 2, 4]  # 1s, 2s, 4s per D-12
        result = {"success": False, "error": "No execution attempted", "data": None}

        for attempt in range(max_retries):
            logger.info(
                "Tool execution attempt",
                tool=tool_name,
                attempt=attempt + 1,
                max_retries=max_retries,
            )

            result = await self._execute_tool(tool_name, params, context)

            if result.get("success"):
                return result

            error = result.get("error", "")

            # Check if error is retryable
            if not self._is_retryable_error(error):
                # Non-retryable error, skip retry layer
                logger.warning(
                    "Non-retryable error encountered", tool=tool_name, error=error
                )
                break

            # Wait before next retry (exponential backoff)
            if attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                logger.info(
                    "Retrying after delay",
                    tool=tool_name,
                    delay_seconds=delay,
                    next_attempt=attempt + 2,
                )
                await asyncio.sleep(delay)

        # Layer 2: Try alternative tool
        alternative_tool = self._get_alternative_tool(tool_name)

        if alternative_tool:
            logger.info(
                "Trying alternative tool",
                primary_tool=tool_name,
                alternative_tool=alternative_tool,
            )

            alternative_result = await self._execute_tool(
                alternative_tool, params, context
            )

            if alternative_result.get("success"):
                return {
                    "success": True,
                    "data": alternative_result.get("data"),
                    "error": None,
                    "used_alternative": True,
                    "alternative_tool": alternative_tool,
                }

        # Layer 3: User decision needed
        logger.warning(
            "All recovery options exhausted, needs user decision",
            tool=tool_name,
            error=result.get("error", "Unknown error"),
        )

        suggestion = f"The tool '{tool_name}' failed after {max_retries} attempts."
        if alternative_tool:
            suggestion += f" Alternative tool '{alternative_tool}' also failed."
        suggestion += " Please check your request or try a different approach."

        return {
            "success": False,
            "error": result.get("error", "Tool execution failed"),
            "data": None,
            "needs_user_decision": True,
            "suggestion": suggestion,
            "alternatives": ["Try a different query", "Check if service is available"],
        }

    async def resume_with_tool(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        confirmed: bool = True,
    ) -> Dict[str, Any]:
        """Resume execution after user confirmation.

        Args:
            session_id: Session ID
            tool_name: Tool to execute after confirmation
            parameters: Tool parameters
            confirmed: Whether user confirmed (default: True)

        Returns:
            Execution result dict
        """
        if not confirmed:
            logger.info("User declined tool execution", tool=tool_name)
            self.current_state = AgentState.PAUSED

            return {
                "success": False,
                "error": "User declined tool execution",
                "state": self.current_state.value,
            }

        logger.info("Resuming with confirmed tool", tool=tool_name)

        # Build context
        context = await self.context_manager.build_context(session_id)

        # Execute confirmed tool
        self.current_state = AgentState.TOOL_EXECUTION
        tool_result = await self._execute_tool(tool_name, parameters, context)

        # Continue execution from this point
        # (Simplified - full implementation would rebuild messages and continue loop)

        return {
            "success": tool_result.get("success"),
            "tool_result": tool_result,
            "state": self.current_state.value,
        }

    def _build_system_prompt(self, context: Context) -> str:
        """Build system prompt for agent with reasoning framework per D-11.

        Per D-11: Enhanced system prompt includes:
        1. Explicit reasoning framework (Analyze → Select → Plan → Verify)
        2. Error handling strategy guidance
        3. Clear tool categorization

        Args:
            context: Execution context

        Returns:
            System prompt string
        """
        objective = context.objective

        prompt = f"""You are an intelligent academic assistant helping researchers manage their paper library and research workflow.

User's objective: {objective}

## REASONING FRAMEWORK (Per D-11)

Before each action, follow these reasoning steps:

1. ANALYZE INTENT: What does the user want to accomplish?
   - Understand the goal behind the request
   - Identify key information needed

2. SELECT TOOLS: Which tools can help achieve this goal?
   - Consider tool capabilities and limitations
   - Choose the most appropriate tool for the task

3. PLAN EXECUTION: What order should tools be called?
   - Determine sequence of operations
   - Consider dependencies between tools

4. VERIFY RESULTS: How to confirm the task is complete?
   - Check if results match user expectations
   - Validate output quality and completeness

## AVAILABLE TOOLS

**Query Tools (Level 1: Auto-execute, no confirmation needed):**
- external_search: Search external databases (arXiv, Semantic Scholar, CrossRef)
- rag_search: Query user's paper library using RAG
- list_papers: List papers with filters
- read_paper: Read paper details
- list_notes: List user's notes
- read_note: Read note content
- extract_references: Extract reference list from papers

**Write Tools (Level 2: Log audit, no confirmation needed):**
- create_note: Create a new note
- update_note: Update an existing note
- merge_documents: Merge content from multiple sources

**Dangerous Tools (Level 3: Requires user confirmation):**
- upload_paper: Upload a new paper (requires confirmation)
- delete_paper: Delete a paper (requires confirmation)
- execute_command: Execute system command (requires confirmation)

## ERROR HANDLING STRATEGY (Per D-12)

When a tool fails, apply multi-layer recovery:

1. **Retry**: Transient errors (timeout, network) are automatically retried 3 times
2. **Alternative**: If retry fails, try alternative tools (e.g., external_search → rag_search)
3. **User Decision**: If all recovery fails, explain the error and suggest solutions

Guidelines for error recovery:
- Do NOT retry on "not found", "permission denied", or "invalid" errors
- Always retry on "timeout", "network", or "unavailable" errors
- When selecting alternatives, consider tool capabilities

## EXECUTION GUIDELINES

- Be concise and efficient
- Use minimal tool calls to achieve the objective
- Apply reasoning framework before each action
- If a tool fails, apply error recovery strategy
- Provide clear explanations for your actions
- When the objective is complete, provide a final answer

## CURRENT ENVIRONMENT

- User ID: {context.environment.get("user_id", "unknown")}
- Session ID: {context.environment.get("session_id", "unknown")}
"""

        return prompt

    def _build_messages(
        self, context: Context, user_input: str
    ) -> List[Dict[str, Any]]:
        """Build messages list for LLM.

        Args:
            context: Execution context
            user_input: Current user input

        Returns:
            List of message dicts
        """
        messages = []

        # Add important messages from context
        for msg in context.important_messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return messages
