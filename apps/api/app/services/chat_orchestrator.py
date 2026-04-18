"""Chat orchestrator for Agent execution and SSE streaming.

Per D-07: Orchestrator layer for chat execution, separating coordination from business logic.

Responsibilities:
- Agent execution coordination
- SSE event generation and streaming with message_id binding (HARD RULE 0.2)
- Phase inference from raw events
- Confirmation request handling with Redis persistence
- Real-time event callback management

Sprint 3: Confirmation mechanism closure with Redis state persistence.
Phase 1.3: message_id binding + phase inference + event orchestration.
"""

import json
import uuid
import asyncio
from asyncio import Queue
from datetime import datetime, timezone, timedelta
from typing import AsyncIterator, Any, Dict, Optional, Tuple, Literal

import redis.asyncio as redis

from app.core.agent_runner import AgentRunner
from app.utils.agent_init import initialize_agent_components
from app.models.chat import (
    SSEEventType,
    SSEEventEnvelope,
    AgentPhase,
    TaskType,
    SessionStartEventData,
    PhaseEventData,
    ReasoningEventData,
    MessageEventData,
    ToolCallEventData,
    ToolResultEventData,
    CitationEventData,
    RoutingDecisionEventData,
    CancelEventData,
    DoneEventData,
    ErrorEventData,
    ConfirmationRequiredEventData,
    ThoughtEventData,  # Legacy
    MessageEventData as LegacyMessageEventData,  # Legacy
    ToolCallEventData as LegacyToolCallEventData,  # Legacy
    ToolResultEventData as LegacyToolResultEventData,  # Legacy
)
from app.models.confirmation import ConfirmationState
from app.services.message_service import message_service
from app.config import settings
from app.core.observability.context import set_run_context
from app.core.observability.events import build_event
from app.utils.logger import logger, bind_run_context, clear_observability_context


# ============================================================
# Phase Inference Constants (HARD RULE 0.2)
# ============================================================

PHASE_LABELS: Dict[AgentPhase, str] = {
    "idle": "",
    "analyzing": "分析问题中",
    "retrieving": "检索知识库中",
    "reading": "阅读论文中",
    "tool_calling": "调用工具中",
    "synthesizing": "组织回答中",
    "verifying": "验证引用中",
    "done": "回答完成",
    "error": "发生错误",
    "cancelled": "已取消",
}

# Tool name to phase mapping for inference
TOOL_PHASE_MAPPING: Dict[str, AgentPhase] = {
    "rag_search": "retrieving",
    "search_papers": "retrieving",
    "get_paper": "reading",
    "get_paper_by_id": "reading",
    "download_paper": "reading",
    "compare_papers": "reading",
    "get_citations": "verifying",
    "web_search": "retrieving",
    "execute_sql": "tool_calling",
    "default": "tool_calling",
}


class ChatOrchestrator:
    """Orchestrator for Agent execution with SSE streaming.

    HARD RULE 0.2: Each SSE event must bind to current assistant message ID.
    """

    # Confirmation expiry: 1 hour (Sprint 3)
    CONFIRMATION_EXPIRY = 3600

    # ============================================================
    # Phase Inference Logic (HARD RULE 0.2)
    # ============================================================

    def _infer_phase_from_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        previous_phase: AgentPhase = "idle",
    ) -> AgentPhase:
        """Infer user-friendly phase from raw event.

        Phase transition logic:
        - reasoning -> analyzing (first) / synthesizing (after tool_result)
        - content -> synthesizing
        - tool_call -> tool_calling (or specific phase by tool name)
        - tool_result -> reading / retrieving (based on tool)
        - error -> error
        - done -> done

        Args:
            event_type: Raw event type (reasoning, content, tool_call, etc.)
            event_data: Event data payload
            previous_phase: Previous phase for context

        Returns:
            Inferred AgentPhase
        """
        if event_type == "reasoning":
            # First reasoning chunk: analyzing
            # After tool results: synthesizing
            if previous_phase in ("idle", "analyzing"):
                return "analyzing"
            elif previous_phase in ("retrieving", "reading", "tool_calling", "verifying"):
                return "synthesizing"
            return previous_phase or "analyzing"

        elif event_type == "content":
            # Content generation: synthesizing
            return "synthesizing"

        elif event_type == "tool_call":
            tool_name = event_data.get("name", event_data.get("tool", "unknown"))
            # Infer specific phase from tool name
            phase = TOOL_PHASE_MAPPING.get(tool_name, TOOL_PHASE_MAPPING.get("default", "tool_calling"))
            return phase

        elif event_type == "tool_result":
            tool_name = event_data.get("tool", "unknown")
            success = event_data.get("success", False)
            # After retrieval tool: reading
            if tool_name in ("rag_search", "search_papers"):
                return "reading" if success else "error"
            # After reading tool: synthesizing
            elif tool_name in ("get_paper", "get_paper_by_id", "compare_papers"):
                return "synthesizing" if success else "error"
            return previous_phase

        elif event_type in ("error", "agent_error"):
            return "error"

        elif event_type in ("done", "agent_complete"):
            return "done"

        elif event_type == "cancel":
            return "cancelled"

        elif event_type == "confirmation_required":
            return "tool_calling"

        # Default: keep previous phase
        return previous_phase

    def _get_phase_label(self, phase: AgentPhase) -> str:
        """Get user-friendly label for phase.

        Args:
            phase: AgentPhase enum value

        Returns:
            Chinese label string
        """
        return PHASE_LABELS.get(phase, "")

    # ============================================================
    # Message ID Binding (HARD RULE 0.2)
    # ============================================================

    async def _create_assistant_message(
        self,
        session_id: str,
        user_id: str,
    ) -> str:
        """Create empty assistant message for message_id binding.

        HARD RULE 0.2: Every user message triggers immediate assistant message creation.

        Args:
            session_id: Session UUID
            user_id: User UUID

        Returns:
            Created message_id
        """
        message_id = await message_service.save_message(
            session_id=session_id,
            role="assistant",
            content="",  # Empty initially, will be updated later
        )

        logger.info(
            "Assistant message created for binding",
            message_id=message_id,
            session_id=session_id,
        )

        return message_id

    async def _update_assistant_message(
        self,
        message_id: str,
        content: str,
    ) -> None:
        """Update assistant message content after streaming completes.

        Args:
            message_id: Message UUID
            content: Final content
        """
        # Note: message_service.save_message creates new messages
        # For updates, we would need to add update_message method
        # For now, we log the update intent
        logger.info(
            "Assistant message update requested",
            message_id=message_id,
            content_length=len(content),
        )
        # TODO: Implement message update in message_service

    def _close_message_binding(self, message_id: str | None, final_phase: AgentPhase) -> None:
        """Close current message_id binding.

        Called after done/error/cancel events.
        """
        logger.info(
            "Message binding closed",
            message_id=message_id,
            final_phase=final_phase,
        )

    # ============================================================
    # SSE Event Formatting
    # ============================================================

    async def stream_sse_event(
        self,
        event_type: str,
        data: dict,
        message_id: str | None = None,
        event_id: str | None = None,
    ) -> str:
        """Format SSE event as string with message_id binding.

        Args:
            event_type: SSE event type (thought, tool_call, message, etc.)
            data: Event data payload
            message_id: Required message_id for binding (HARD RULE 0.2)
            event_id: Optional event ID for replay (Last-Event-ID mechanism)

        Returns:
            SSE formatted string:
            "id: {event_id}\\nevent: {type}\\ndata: {json}\\n\\n"

        Reference: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
        """
        bound_message_id = message_id

        # Build SSE envelope with message_id
        envelope = SSEEventEnvelope(
            event=event_type,
            data=data,
            message_id=bound_message_id or "",  # Empty if no binding
        )

        id_line = f"id: {event_id}\n" if event_id else ""
        event_line = f"event: {event_type}\n"
        # Include message_id in data for frontend binding
        data_with_binding = {**data, "message_id": bound_message_id}
        data_line = f"data: {json.dumps(data_with_binding)}\n\n"

        return f"{id_line}{event_line}{data_line}"

    async def stream_sse_event_v2(
        self,
        event_type: str,
        data: dict,
        message_id: str,
        event_id: str | None = None,
    ) -> str:
        """Format SSE event with SSEEventEnvelope structure (v2).

        Args:
            event_type: SSE event type
            data: Event data payload
            message_id: Required message_id (HARD RULE 0.2)
            event_id: Optional event ID for replay

        Returns:
            SSE formatted string with envelope structure
        """
        envelope = SSEEventEnvelope(
            event=event_type,
            data=data,
            message_id=message_id,
        )

        id_line = f"id: {event_id}\n" if event_id else ""
        event_line = f"event: {event_type}\n"
        data_line = f"data: {json.dumps(envelope.model_dump())}\n\n"

        return f"{id_line}{event_line}{data_line}"

    async def handle_confirmation_required(
        self,
        session_id: str,
        user_id: str,
        message_id: str,
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
            message_id=message_id,
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
        final_phase: AgentPhase = "cancelled"

        if not state:
            yield await self.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error="Confirmation not found or expired",
                    details={"confirmation_id": confirmation_id},
                ).model_dump(),
                message_id="",
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
                message_id=state.message_id,
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
                message_id=state.message_id,
            )
            return

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        processing_key = f"confirmation:{confirmation_id}:processing"
        acquired = await r.set(processing_key, "1", ex=self.CONFIRMATION_EXPIRY, nx=True)
        if not acquired:
            yield await self.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error="Confirmation is already being processed",
                    details={"confirmation_id": confirmation_id},
                ).model_dump(),
                message_id=state.message_id,
            )
            return

        try:
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
                    message_id=state.message_id,
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
                        message_id=state.message_id,
                    )

                    # Emit done event
                    yield await self.stream_sse_event(
                        SSEEventType.DONE,
                        {
                            "type": "done",
                            "content": "[DONE]",
                            "message": "Tool executed successfully. Agent resumed.",
                        },
                        message_id=state.message_id,
                    )
                    final_phase = "done"

                except Exception as e:
                    logger.error("Tool execution failed after confirmation", error=str(e))
                    yield await self.stream_sse_event(
                        SSEEventType.ERROR,
                        ErrorEventData(
                            type="error",
                            error=str(e),
                            details={"tool": state.tool_name},
                        ).model_dump(),
                        message_id=state.message_id,
                    )
                    final_phase = "error"
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
                    message_id=state.message_id,
                )

                # Emit done event
                yield await self.stream_sse_event(
                    SSEEventType.DONE,
                    {
                        "type": "done",
                        "content": "[DONE]",
                        "message": "Tool rejected. Agent stopped.",
                    },
                    message_id=state.message_id,
                )
                final_phase = "cancelled"
        finally:
            # Clear confirmation from Redis and close observability context for resume flow.
            await r.delete(f"confirmation:{confirmation_id}")
            await r.delete(processing_key)
            self._close_message_binding(message_id=state.message_id, final_phase=final_phase)
            clear_observability_context()

    async def execute_with_streaming(
        self,
        user_input: str,
        session_id: str,
        user_id: str,
        auto_confirm: bool = False,
        mode: str = "auto",
        scope: Optional[Dict[str, Any]] = None,
        task_type: TaskType = "general",
    ) -> AsyncIterator[str]:
        """Execute Agent with real-time SSE streaming.

        HARD RULE 0.2 Implementation:
        1. Create assistant message immediately for message_id binding
        2. Emit session_start event with message_id
        3. Infer phase from raw events and emit phase events
        4. All SSE events carry message_id
        5. Close message binding after done/error/cancel

        Args:
            user_input: User message
            session_id: Session UUID
            user_id: User UUID
            auto_confirm: Auto-confirm dangerous operations
            mode: Execution mode (auto|rag|agent)
            scope: Optional scope ({type: paper|knowledge_base|general, ...})
            task_type: Task type for routing (single_paper, kb_qa, compare, general)

        Yields:
            SSE event strings with message_id binding
        """
        run_id = str(uuid.uuid4())
        set_run_context(run_id=run_id, session_id=session_id)

        # ============================================================
        # Step 1: Create assistant message for binding (HARD RULE 0.2)
        # ============================================================
        message_id = await self._create_assistant_message(
            session_id=session_id,
            user_id=user_id,
        )
        bind_run_context(run_id=run_id, session_id=session_id, message_id=message_id)
        logger.info(
            "run_started",
            **build_event(
                event_type="run_started",
                status="started",
                run_id=run_id,
                session_id=session_id,
                message_id=message_id,
                task_type=task_type,
                mode=mode,
                scope_type=(scope or {}).get("type"),
            ),
        )

        runner, _, _, _ = initialize_agent_components()

        event_queue: Queue[Tuple[str, dict]] = Queue()
        event_counter = 0  # Track event IDs for SSE replay
        reasoning_seq = 0  # Sequence number for reasoning chunks
        content_seq = 0  # Sequence number for content chunks
        accumulated_content = ""  # Track final content for message update

        # ============================================================
        # Step 2: Emit session_start event
        # ============================================================
        event_id = f"{session_id}:{event_counter}"
        event_counter += 1
        yield await self.stream_sse_event_v2(
            SSEEventType.SESSION_START,
            SessionStartEventData(
                session_id=session_id,
                task_type=task_type,
                message_id=message_id,
            ).model_dump(),
            message_id=message_id,
            event_id=event_id,
        )

        # ============================================================
        # Step 3: Emit initial phase event (analyzing)
        # ============================================================
        current_phase: AgentPhase = "analyzing"
        event_id = f"{session_id}:{event_counter}"
        event_counter += 1
        yield await self.stream_sse_event_v2(
            SSEEventType.PHASE,
            PhaseEventData(
                phase="analyzing",
                label=self._get_phase_label("analyzing"),
            ).model_dump(),
            message_id=message_id,
            event_id=event_id,
        )

        async def event_callback(event_type: str, data: Dict[str, Any]):
            """Push real-time events to SSE queue."""
            await event_queue.put((event_type, data))

        # Set event callback on runner instance
        runner.event_callback = event_callback

        async def run_agent():
            """Execute agent and push completion signal."""
            try:
                result = await runner.execute(
                    user_input=user_input,
                    session_id=session_id,
                    user_id=user_id,
                    auto_confirm=auto_confirm,
                )
                await event_queue.put(("agent_complete", result))
            except Exception as e:
                logger.error("Agent execution error", error=str(e))
                await event_queue.put(("agent_error", {"error": str(e)}))

        agent_task = asyncio.create_task(run_agent())

        # ============================================================
        # Step 4: Event loop with phase inference and message_id binding
        # ============================================================
        try:
            while True:
                event_type, event_data = await event_queue.get()

                # Infer phase from event
                new_phase = self._infer_phase_from_event(
                    event_type=event_type,
                    event_data=event_data,
                    previous_phase=current_phase,
                )

                # Emit phase event if changed
                if new_phase != current_phase and new_phase not in ("idle", "done", "error", "cancelled"):
                    current_phase = new_phase
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event_v2(
                        SSEEventType.PHASE,
                        PhaseEventData(
                            phase=new_phase,
                            label=self._get_phase_label(new_phase),
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                # ============================================================
                # Handle different event types
                # ============================================================

                if event_type == "thought":
                    # Legacy thought event - convert to reasoning
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    reasoning_seq += 1
                    content_chunk = event_data.get("content", "")
                    yield await self.stream_sse_event_v2(
                        SSEEventType.REASONING,
                        ReasoningEventData(
                            delta=content_chunk,
                            seq=reasoning_seq,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                elif event_type == "reasoning":
                    # Raw reasoning event from _think_stream
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    reasoning_seq += 1
                    content_chunk = event_data.get("content", "")
                    yield await self.stream_sse_event_v2(
                        SSEEventType.REASONING,
                        ReasoningEventData(
                            delta=content_chunk,
                            seq=reasoning_seq,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                elif event_type == "content":
                    # Raw content event from _think_stream
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    content_seq += 1
                    content_chunk = event_data.get("content", "")
                    accumulated_content += content_chunk
                    yield await self.stream_sse_event_v2(
                        SSEEventType.MESSAGE,
                        MessageEventData(
                            delta=content_chunk,
                            seq=content_seq,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                elif event_type == "tool_call":
                    tool_name = event_data.get("tool", event_data.get("name", "unknown"))
                    tool_id = event_data.get("id", f"tool_{event_counter}")
                    tool_params = event_data.get("parameters", event_data.get("arguments", {}))

                    # Infer tool label
                    tool_label = self._get_tool_label(tool_name)

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event_v2(
                        SSEEventType.TOOL_CALL,
                        ToolCallEventData(
                            id=tool_id,
                            tool=tool_name,
                            label=tool_label,
                            status="running",
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                elif event_type == "tool_result":
                    tool_name = event_data.get("tool", "unknown")
                    tool_id = event_data.get("id", f"tool_{event_counter}")
                    success = event_data.get("success", False)
                    error_msg = event_data.get("error")
                    data_summary = event_data.get("data")

                    # Build summary text
                    summary = self._build_tool_result_summary(tool_name, success, data_summary)

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event_v2(
                        SSEEventType.TOOL_RESULT,
                        ToolResultEventData(
                            id=tool_id,
                            tool=tool_name,
                            label=self._get_tool_label(tool_name),
                            status="success" if success else "failed",
                            summary=summary,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                elif event_type == "agent_complete":
                    result = event_data

                    if result.get("needs_confirmation"):
                        # Persist confirmation state in Redis
                        confirmation_state = await self.handle_confirmation_required(
                            session_id=session_id,
                            user_id=user_id,
                            message_id=message_id,
                            tool_name=result.get("tool_name", "unknown"),
                            parameters=result.get("tool_parameters", {}),
                        )

                        # Emit phase event for tool_calling
                        current_phase = "tool_calling"
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
                            SSEEventType.PHASE,
                            PhaseEventData(
                                phase="tool_calling",
                                label=self._get_phase_label("tool_calling"),
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                        # Emit confirmation_required event
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
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
                            message_id=message_id,
                            event_id=event_id,
                        )
                        # Don't close binding yet - waiting for user response
                        break

                    if result.get("success"):
                        final_content = result.get("answer", accumulated_content)

                        # Update message content if different from accumulated
                        if final_content != accumulated_content:
                            # Send final content chunk if needed
                            if not accumulated_content:
                                event_id = f"{session_id}:{event_counter}"
                                event_counter += 1
                                yield await self.stream_sse_event_v2(
                                    SSEEventType.MESSAGE,
                                    MessageEventData(
                                        delta=final_content,
                                        seq=0,
                                    ).model_dump(),
                                    message_id=message_id,
                                    event_id=event_id,
                                )

                        # Emit done phase
                        current_phase = "done"
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
                            SSEEventType.PHASE,
                            PhaseEventData(
                                phase="done",
                                label=self._get_phase_label("done"),
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                        # Emit done event
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
                            SSEEventType.DONE,
                            DoneEventData(
                                finish_reason="stop",
                                tokens_used=result.get("tokens_used"),
                                cost=result.get("cost"),
                                total_time_ms=result.get("total_time_ms"),
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                        # Update assistant message content
                        await self._update_assistant_message(message_id, final_content)

                    else:
                        # Emit error phase
                        current_phase = "error"
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
                            SSEEventType.PHASE,
                            PhaseEventData(
                                phase="error",
                                label=self._get_phase_label("error"),
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                        # Emit error event
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await self.stream_sse_event_v2(
                            SSEEventType.ERROR,
                            ErrorEventData(
                                code="execution_failed",
                                message=result.get("error", "Unknown error"),
                                recoverable=False,
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                    # Close message binding
                    logger.info(
                        "run_completed",
                        **build_event(
                            event_type="run_completed",
                            status="completed",
                            run_id=run_id,
                            session_id=session_id,
                            message_id=message_id,
                            phase=current_phase,
                            duration_ms=result.get("total_time_ms"),
                            success=bool(result.get("success")),
                        ),
                    )
                    self._close_message_binding(message_id=message_id, final_phase=current_phase)
                    break

                elif event_type == "agent_error":
                    # Emit error phase
                    current_phase = "error"
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event_v2(
                        SSEEventType.PHASE,
                        PhaseEventData(
                            phase="error",
                            label=self._get_phase_label("error"),
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                    # Emit error event
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await self.stream_sse_event_v2(
                        SSEEventType.ERROR,
                        ErrorEventData(
                            code="agent_error",
                            message=event_data.get("error", "Unknown error"),
                            recoverable=True,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                    # Close message binding
                    logger.error(
                        "run_failed",
                        **build_event(
                            event_type="run_failed",
                            status="error",
                            run_id=run_id,
                            session_id=session_id,
                            message_id=message_id,
                            phase="error",
                            error=event_data.get("error", "Unknown error"),
                        ),
                    )
                    self._close_message_binding(message_id=message_id, final_phase=current_phase)
                    break

            await agent_task
        finally:
            if not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
            clear_observability_context()

    # ============================================================
    # Helper methods for event formatting
    # ============================================================

    def _get_tool_label(self, tool_name: str) -> str:
        """Get user-friendly label for tool.

        Args:
            tool_name: Tool name from registry

        Returns:
            Chinese label string
        """
        TOOL_LABELS = {
            "rag_search": "检索知识库",
            "search_papers": "搜索论文",
            "get_paper": "获取论文",
            "get_paper_by_id": "获取论文",
            "download_paper": "下载论文",
            "compare_papers": "对比论文",
            "get_citations": "验证引用",
            "web_search": "网络搜索",
            "execute_sql": "执行查询",
        }
        return TOOL_LABELS.get(tool_name, f"调用 {tool_name}")

    def _build_tool_result_summary(
        self,
        tool_name: str,
        success: bool,
        data: Any,
    ) -> Optional[str]:
        """Build user-friendly summary for tool result.

        Args:
            tool_name: Tool name
            success: Execution success
            data: Result data

        Returns:
            Summary string or None
        """
        if not success:
            return None

        # Build summary based on tool and result
        if tool_name in ("rag_search", "search_papers"):
            if isinstance(data, dict):
                count = data.get("total", data.get("count", 0))
                return f"命中 {count} 篇论文"
            return "检索完成"

        elif tool_name in ("get_paper", "get_paper_by_id"):
            if isinstance(data, dict):
                title = data.get("title", "")
                if title:
                    return f"获取《{title[:30]}...》"
            return "论文获取成功"

        elif tool_name == "compare_papers":
            return "论文对比完成"

        elif tool_name == "web_search":
            if isinstance(data, dict):
                count = data.get("results_count", 0)
                return f"找到 {count} 条结果"
            return "网络搜索完成"

        return None


chat_orchestrator = ChatOrchestrator()
