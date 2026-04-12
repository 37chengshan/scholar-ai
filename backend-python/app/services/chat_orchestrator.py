"""Chat orchestrator for Agent execution and SSE streaming.

Per D-07: Orchestrator layer for chat execution, separating coordination from business logic.

Responsibilities:
- Agent execution coordination
- SSE event generation and streaming
- Confirmation request handling with Redis persistence
- Real-time event callback management

Sprint 3: Confirmation mechanism closure with Redis state persistence.
"""

import json
import uuid
import asyncio
from asyncio import Queue
from datetime import datetime, timezone, timedelta
from typing import AsyncIterator, Any, Dict, Optional, Tuple

import redis.asyncio as redis

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
from app.models.confirmation import ConfirmationState
from app.config import settings
from app.utils.logger import logger


class ChatOrchestrator:
    """Orchestrator for Agent execution with SSE streaming."""

    # Confirmation expiry: 1 hour (Sprint 3)
    CONFIRMATION_EXPIRY = 3600

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

    async def handle_confirmation_required(
        self,
        session_id: str,
        user_id: str,
        tool_name: str,
        parameters: dict,
    ) -> ConfirmationState:
        """Store confirmation state in Redis and return confirmation_id.

        Sprint 3: Confirmation persistence for resume mechanism.

        Args:
            session_id: Session ID for Agent resumption
            user_id: User ID for ownership validation
            tool_name: Tool requiring confirmation
            parameters: Tool execution parameters

        Returns:
            ConfirmationState with confirmation_id and expires_at
        """
        confirmation_id = str(uuid.uuid4())

        # Create confirmation state
        state = ConfirmationState(
            confirmation_id=confirmation_id,
            session_id=session_id,
            user_id=user_id,
            tool_name=tool_name,
            parameters=parameters,
            status="pending",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=self.CONFIRMATION_EXPIRY),
        )

        # Store in Redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"confirmation:{confirmation_id}"

        await r.setex(
            key,
            self.CONFIRMATION_EXPIRY,
            state.model_dump_json(),
        )

        # Also store by session for cleanup
        session_key = f"session:{session_id}:confirmations"
        await r.sadd(session_key, confirmation_id)
        await r.expire(session_key, self.CONFIRMATION_EXPIRY)

        logger.info(
            "Confirmation state persisted",
            confirmation_id=confirmation_id,
            tool_name=tool_name,
            session_id=session_id,
            expires_in_seconds=self.CONFIRMATION_EXPIRY,
        )

        return state

    async def get_confirmation_state(
        self,
        confirmation_id: str,
    ) -> ConfirmationState | None:
        """Get confirmation state from Redis.

        Args:
            confirmation_id: Confirmation ID

        Returns:
            ConfirmationState if found, None if expired/not found
        """
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"confirmation:{confirmation_id}"

        state_json = await r.get(key)

        if not state_json:
            logger.warning(
                "Confirmation not found or expired",
                confirmation_id=confirmation_id,
            )
            return None

        return ConfirmationState.model_validate_json(state_json)

    async def update_confirmation_status(
        self,
        confirmation_id: str,
        status: str,
    ) -> None:
        """Update confirmation status in Redis.

        Args:
            confirmation_id: Confirmation ID
            status: New status (approved/rejected)
        """
        state = await self.get_confirmation_state(confirmation_id)
        if not state:
            raise ValueError("Confirmation not found")

        state.status = status

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"confirmation:{confirmation_id}"

        await r.setex(
            key,
            self.CONFIRMATION_EXPIRY,
            state.model_dump_json(),
        )

        logger.info(
            "Confirmation status updated",
            confirmation_id=confirmation_id,
            status=status,
        )

    async def resume_with_confirmation(
        self,
        confirmation_id: str,
        approved: bool,
    ) -> AsyncIterator[str]:
        """Resume Agent execution after user confirmation.

        Sprint 3: Resume mechanism for confirmation closure.

        Args:
            confirmation_id: Confirmation ID
            approved: Whether user approved tool execution

        Yields:
            SSE events for tool execution and continuation
        """
        # Get state
        state = await self.get_confirmation_state(confirmation_id)

        if not state:
            yield await self.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error="Confirmation not found or expired",
                    details={"confirmation_id": confirmation_id},
                ).model_dump(),
            )
            return

        if state.is_expired():
            yield await self.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error="Confirmation expired",
                    details={
                        "confirmation_id": confirmation_id,
                        "expires_at": state.expires_at.isoformat(),
                    },
                ).model_dump(),
            )
            return

        if state.status != "pending":
            yield await self.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error=f"Confirmation already {state.status}",
                    details={
                        "confirmation_id": confirmation_id,
                        "status": state.status,
                    },
                ).model_dump(),
            )
            return

        # Update status
        status = "approved" if approved else "rejected"
        await self.update_confirmation_status(confirmation_id, status)

        # Get runner for resumption
        runner, _, _, _ = initialize_agent_components()

        logger.info(
            "Agent resuming after confirmation",
            confirmation_id=confirmation_id,
            approved=approved,
            tool_name=state.tool_name,
            session_id=state.session_id,
        )

        if approved:
            # Emit tool_call event
            yield await self.stream_sse_event(
                SSEEventType.TOOL_CALL,
                ToolCallEventData(
                    type="tool_call",
                    tool=state.tool_name,
                    parameters=state.parameters,
                ).model_dump(),
            )

            # Resume with tool execution
            try:
                result = await runner.resume_with_tool(
                    session_id=state.session_id,
                    tool_name=state.tool_name,
                    parameters=state.parameters,
                    confirmed=True,
                )

                # Emit tool_result event
                yield await self.stream_sse_event(
                    SSEEventType.TOOL_RESULT,
                    ToolResultEventData(
                        type="tool_result",
                        tool=state.tool_name,
                        success=result.get("success", False),
                        data=result.get("data"),
                        error=result.get("error"),
                    ).model_dump(),
                )

                # Emit done event
                yield await self.stream_sse_event(
                    SSEEventType.DONE,
                    {
                        "type": "done",
                        "content": "[DONE]",
                        "message": "Tool executed successfully. Agent resumed.",
                    },
                )

            except Exception as e:
                logger.error("Tool execution failed after confirmation", error=str(e))
                yield await self.stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        type="error",
                        error=str(e),
                        details={"tool": state.tool_name},
                    ).model_dump(),
                )
        else:
            # Emit tool_rejected event (new event type for Sprint 3)
            yield await self.stream_sse_event(
                "tool_rejected",
                {
                    "type": "tool_rejected",
                    "tool": state.tool_name,
                    "reason": "User rejected",
                    "message": f"Tool {state.tool_name} was rejected by user",
                },
            )

            # Emit done event
            yield await self.stream_sse_event(
                SSEEventType.DONE,
                {
                    "type": "done",
                    "content": "[DONE]",
                    "message": "Tool rejected. Agent stopped.",
                },
            )

        # Clear confirmation from Redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.delete(f"confirmation:{confirmation_id}")

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
                    # Sprint 3: Persist confirmation state in Redis
                    confirmation_state = await self.handle_confirmation_required(
                        session_id=session_id,
                        user_id=user_id,
                        tool_name=result.get("tool_name", "unknown"),
                        parameters=result.get("tool_parameters", {}),
                    )

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event(
                        SSEEventType.CONFIRMATION_REQUIRED,
                        ConfirmationRequiredEventData(
                            type="confirmation_required",
                            confirmation_id=confirmation_state.confirmation_id,
                            message=result.get(
                                "message",
                                "Agent wants to execute a dangerous operation",
                            ),
                            tool_name=confirmation_state.tool_name,
                            parameters=confirmation_state.parameters,
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
