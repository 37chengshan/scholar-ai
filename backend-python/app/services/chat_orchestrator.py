"""Chat orchestrator for Agent execution and SSE streaming.

Per D-07: Orchestrator layer for chat execution, separating coordination from business logic.

Responsibilities:
- Agent execution coordination
- SSE event generation and streaming
- Confirmation request handling
- Real-time event callback management
"""

import json
import uuid
import asyncio
from asyncio import Queue
from datetime import datetime, timezone
from typing import AsyncIterator, Any, Dict, Optional, Tuple

from app.core.agent_runner import AgentRunner
from app.utils.agent_init import initialize_agent_components
from app.models.chat import (
    SSEEventType,
    ThoughtEventData,
    ToolCallEventData,
    ToolResultEventData,
    ConfirmationRequiredEventData,
    MessageEventData,
    ErrorEventData,
)
from app.utils.logger import logger


class ChatOrchestrator:
    """Orchestrator for Agent execution with SSE streaming."""

    async def stream_sse_event(
        self, event_type: str, data: dict, event_id: str | None = None
    ) -> str:
        """Format SSE event as string.

        Args:
            event_type: SSE event type (thought, tool_call, message, etc.)
            data: Event data payload
            event_id: Optional event ID for replay (Last-Event-ID mechanism)

        Returns:
            SSE formatted string with optional id line:
            "id: {event_id}\\nevent: {type}\\ndata: {json}\\n\\n"

        Reference: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
        """
        id_line = f"id: {event_id}\n" if event_id else ""
        event_line = f"event: {event_type}\n"
        data_line = f"data: {json.dumps(data)}\n\n"

        return f"{id_line}{event_line}{data_line}"

    async def execute_with_streaming(
        self,
        user_input: str,
        session_id: str,
        user_id: str,
        auto_confirm: bool = False,
    ) -> AsyncIterator[str]:
        """Execute Agent with real-time SSE streaming.

        Args:
            user_input: User message
            session_id: Session UUID
            user_id: User UUID
            auto_confirm: Auto-confirm dangerous operations

        Yields:
            SSE event strings with id field for Last-Event-ID replay
        """
        runner, _, _, _ = initialize_agent_components()

        event_queue: Queue[Tuple[str, dict]] = Queue()
        event_counter = 0  # Track event IDs for SSE replay

        async def event_callback(event_type: str, data: Dict[str, Any]):
            """Push real-time events to SSE queue."""
            await event_queue.put((event_type, data))

        async def run_agent():
            """Execute agent and push completion signal."""
            try:
                result = await runner.execute(
                    user_input=user_input,
                    session_id=session_id,
                    user_id=user_id,
                    auto_confirm=auto_confirm,
                    event_callback=event_callback,
                )
                await event_queue.put(("agent_complete", result))
            except Exception as e:
                logger.error("Agent execution error", error=str(e))
                await event_queue.put(("agent_error", {"error": str(e)}))

        agent_task = asyncio.create_task(run_agent())

        # Initial thought event with id
        event_id = f"{session_id}:{event_counter}"
        event_counter += 1
        yield await self.stream_sse_event(
            SSEEventType.THOUGHT,
            ThoughtEventData(
                type="thinking", content="Analyzing your request..."
            ).model_dump(),
            event_id=event_id,
        )

        while True:
            event_type, event_data = await event_queue.get()

            if event_type == "thought":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await self.stream_sse_event(
                    SSEEventType.THOUGHT,
                    ThoughtEventData(
                        type="thinking",
                        content=event_data.get("content", ""),
                    ).model_dump(),
                    event_id=event_id,
                )

            elif event_type == "tool_call":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await self.stream_sse_event(
                    SSEEventType.TOOL_CALL,
                    ToolCallEventData(
                        type="tool_call",
                        tool=event_data.get("tool", "unknown"),
                        parameters=event_data.get("parameters", {}),
                    ).model_dump(),
                    event_id=event_id,
                )

            elif event_type == "tool_result":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await self.stream_sse_event(
                    SSEEventType.TOOL_RESULT,
                    ToolResultEventData(
                        type="tool_result",
                        tool=event_data.get("tool", "unknown"),
                        success=event_data.get("success", False),
                        data=event_data.get("data"),
                        error=event_data.get("error"),
                    ).model_dump(),
                    event_id=event_id,
                )

            elif event_type == "agent_complete":
                result = event_data

                if result.get("needs_confirmation"):
                    confirmation_id = str(uuid.uuid4())
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event(
                        SSEEventType.CONFIRMATION_REQUIRED,
                        ConfirmationRequiredEventData(
                            type="confirmation_required",
                            confirmation_id=confirmation_id,
                            message=result.get(
                                "message",
                                "Agent wants to execute a dangerous operation",
                            ),
                            tool_name=result.get("tool_name", "unknown"),
                            parameters=result.get("tool_parameters", {}),
                        ).model_dump(),
                        event_id=event_id,
                    )
                    break

                if result.get("success"):
                    final_content = result.get("answer", "Task completed")
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event(
                        SSEEventType.MESSAGE,
                        MessageEventData(
                            type="message", content=final_content
                        ).model_dump(),
                        event_id=event_id,
                    )

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event(
                        SSEEventType.DONE,
                        {
                            "type": "done",
                            "content": "[DONE]",
                            "tokens_used": result.get("tokens_used", 0),
                            "cost": result.get("cost", 0.0),
                            "iterations": result.get("iterations", 0),
                            "total_time_ms": result.get("total_time_ms", 0),
                        },
                        event_id=event_id,
                    )
                else:
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event(
                        SSEEventType.ERROR,
                        ErrorEventData(
                            type="error",
                            error=result.get("error", "Unknown error"),
                            details={"iterations": result.get("iterations", 0)},
                        ).model_dump(),
                        event_id=event_id,
                    )

                break

            elif event_type == "agent_error":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await self.stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        type="error",
                        error=event_data.get("error", "Unknown error"),
                        details=None,
                    ).model_dump(),
                    event_id=event_id,
                )
                break

        await agent_task


chat_orchestrator = ChatOrchestrator()
