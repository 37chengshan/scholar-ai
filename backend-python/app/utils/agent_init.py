"""Agent initialization utilities.

Provides centralized initialization function for Agent components:
- GLM-4.5-Air LLM client
- Tool Registry with all registered executors
- Safety Layer for permission checks
- Context Manager for conversation history
- Agent Runner for execution

Usage:
    from app.utils.agent_init import initialize_agent_components

    runner, registry, safety_layer, context_manager = initialize_agent_components()
    result = await runner.execute("Find papers about AI", session_id, user_id)
"""

from typing import Tuple

from app.llm.glm_client import GLM45AirClient
from app.core.tool_registry import ToolRegistry
from app.tools import register_all_tools
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager
from app.core.agent_runner import AgentRunner
from app.utils.logger import logger


def initialize_agent_components(max_iterations: int = 10) -> Tuple[AgentRunner, ToolRegistry, SafetyLayer, ContextManager]:
    """Initialize all Agent components for production execution.

    Creates and wires all dependencies:
    1. GLM-4.5-Air LLM client
    2. Tool Registry with 15 registered executors
    3. Safety Layer for permission checks
    4. Context Manager for conversation history
    5. Agent Runner with all dependencies

    Args:
        max_iterations: Maximum Agent execution iterations (default: 10)

    Returns:
        Tuple of (AgentRunner, ToolRegistry, SafetyLayer, ContextManager)

    Example:
        >>> runner, registry, safety, context = initialize_agent_components()
        >>> result = await runner.execute("Find AI papers", session_id, user_id)
    """
    logger.info("Initializing Agent components")

    # 1. Create LLM client
    llm_client = GLM45AirClient()

    # 2. Create Tool Registry and register all tools
    registry = ToolRegistry()
    register_all_tools(registry)

    logger.info(
        "Tool Registry initialized",
        registered_tools=len(registry.tools)
    )

    # 3. Create Safety Layer
    safety_layer = SafetyLayer()

    # 4. Create Context Manager
    context_manager = ContextManager()

    # 5. Create Agent Runner with all dependencies
    runner = AgentRunner(
        llm_client=llm_client,
        tool_registry=registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=max_iterations
    )

    logger.info(
        "Agent Runner initialized",
        max_iterations=max_iterations
    )

    return runner, registry, safety_layer, context_manager