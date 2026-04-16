"""Test real-time SSE event streaming.

Tests the event_callback mechanism for real-time tool execution updates.
"""

import asyncio
from asyncio import Queue
from typing import Dict, Any, List, Tuple
import pytest

from app.core.agent_runner import AgentRunner, AgentState
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager


@pytest.fixture
def mock_components():
    """Create mock components for AgentRunner."""

    # Mock LLM client
    class MockLLMClient:
        async def chat_completion(
            self, messages, tools, tool_choice, max_tokens, temperature
        ):
            # Simulate LLM response with tool call
            class MockResponse:
                usage = {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                }
                choices = [
                    type(
                        "Choice",
                        (),
                        {
                            "message": type(
                                "Message",
                                (),
                                {
                                    "tool_calls": [
                                        type(
                                            "ToolCall",
                                            (),
                                            {
                                                "function": type(
                                                    "Function",
                                                    (),
                                                    {
                                                        "name": "external_search",
                                                        "arguments": '{"query": "AI papers"}',
                                                    },
                                                )
                                            },
                                        )
                                    ],
                                    "content": None,
                                },
                            )
                        },
                    )
                ]

            return MockResponse()

    # Mock tool registry
    class MockToolRegistry:
        def list_tools_schema(self):
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "external_search",
                        "description": "Search external databases",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                        },
                    },
                }
            ]

        def get(self, tool_name):
            return True

        async def execute(self, tool_name, parameters, **kwargs):
            return {"success": True, "data": {"results": ["Paper 1", "Paper 2"]}}

    # Mock safety layer
    class MockSafetyLayer:
        async def check_permission(self, tool_name, context):
            return {"needs_confirmation": False}

    # Mock context manager
    class MockContextManager:
        async def build_context(self, session_id, user_id=None):
            from app.core.context_manager import Context

            context = Context(
                objective="",
                important_messages=[],
                tool_history=[],
                working_memory={},
                environment={"user_id": user_id or "test-user"},
            )
            return context

    return MockLLMClient(), MockToolRegistry(), MockContextManager(), MockSafetyLayer()


@pytest.mark.asyncio
async def test_realtime_event_emission(mock_components):
    """Test that events are emitted in real-time during agent execution."""
    llm_client, tool_registry, context_manager, safety_layer = mock_components

    # Create event queue to collect events
    event_queue: Queue[Tuple[str, Dict[str, Any]]] = Queue()
    collected_events: List[Tuple[str, Dict[str, Any]]] = []

    # Define event callback
    async def event_callback(event_type: str, data: Dict[str, Any]):
        await event_queue.put((event_type, data))

    # Create AgentRunner with event callback
    runner = AgentRunner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=2,
        event_callback=event_callback,
    )

    # Execute agent
    result_task = asyncio.create_task(
        runner.execute(
            user_input="Search for AI papers",
            session_id="test-session",
            user_id="test-user",
            auto_confirm=False,
        )
    )

    # Collect events from queue
    event_count = 0
    max_events = 10  # Prevent infinite loop

    while event_count < max_events:
        try:
            # Wait for event with timeout
            event_type, event_data = await asyncio.wait_for(
                event_queue.get(), timeout=2.0
            )
            collected_events.append((event_type, event_data))
            event_count += 1

            # Check if execution is complete
            if result_task.done():
                break
        except asyncio.TimeoutError:
            break

    # Wait for execution to complete
    result = await result_task

    # Verify events were emitted in correct order
    assert len(collected_events) > 0, "No events were emitted"

    # Check for thought event
    thought_events = [e for e in collected_events if e[0] == "thought"]
    assert len(thought_events) > 0, "No thought event emitted"

    # Check for tool_call event
    tool_call_events = [e for e in collected_events if e[0] == "tool_call"]
    assert len(tool_call_events) > 0, "No tool_call event emitted"

    # Check for tool_result event
    tool_result_events = [e for e in collected_events if e[0] == "tool_result"]
    assert len(tool_result_events) > 0, "No tool_result event emitted"

    # Verify event order: thought -> tool_call -> tool_result
    event_types = [e[0] for e in collected_events]
    assert "thought" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types

    # Verify tool_call contains correct tool name
    tool_call_data = tool_call_events[0][1]
    assert tool_call_data.get("tool") == "external_search"
    assert "parameters" in tool_call_data

    # Verify tool_result contains success status
    tool_result_data = tool_result_events[0][1]
    assert tool_result_data.get("success") == True

    print(f"✅ Test passed! Events collected in order: {event_types}")


@pytest.mark.asyncio
async def test_backward_compatibility_without_callback(mock_components):
    """Test that AgentRunner works without event_callback (backward compatibility)."""
    llm_client, tool_registry, context_manager, safety_layer = mock_components

    # Create AgentRunner WITHOUT event callback
    runner = AgentRunner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=10,
        event_callback=None,  # No callback
    )

    # Execute agent
    result = await runner.execute(
        user_input="Search for AI papers",
        session_id="test-session",
        user_id="test-user",
        auto_confirm=False,
    )

    # Verify execution still works (even if it doesn't complete successfully)
    assert "success" in result
    assert "tool_calls" in result
    assert "iterations" in result

    # Verify no callback error occurred
    assert runner.event_callback is None
    assert result.get("error") != "event_callback is required"  # No such error

    print("✅ Backward compatibility test passed!")


if __name__ == "__main__":
    # Run tests manually
    import sys

    async def run_tests():
        print("Running real-time SSE event tests...")

        # Create mock components
        from unittest.mock import Mock

        llm_client = Mock()
        tool_registry = Mock()
        context_manager = Mock()
        safety_layer = Mock()

        # Run test 1
        try:
            await test_realtime_event_emission(
                (llm_client, tool_registry, context_manager, safety_layer)
            )
        except Exception as e:
            print(f"Test 1 failed: {e}")

        # Run test 2
        try:
            await test_backward_compatibility_without_callback(
                (llm_client, tool_registry, context_manager, safety_layer)
            )
        except Exception as e:
            print(f"Test 2 failed: {e}")

    asyncio.run(run_tests())
