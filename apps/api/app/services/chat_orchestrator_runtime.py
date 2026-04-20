"""Runtime helpers for chat orchestrator streaming and confirmation flows."""

import asyncio
import json
import uuid
from asyncio import Queue
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import redis.asyncio as redis

from app.config import settings
from app.core.observability.context import set_run_context
from app.core.observability.events import build_event
from app.models.chat import (
    AgentPhase,
    ConfirmationRequiredEventData,
    DoneEventData,
    ErrorEventData,
    MessageEventData,
    PhaseEventData,
    ReasoningEventData,
    SSEEventType,
    SessionStartEventData,
    ToolCallEventData,
    ToolResultEventData,
)
from app.models.confirmation import ConfirmationState
from app.utils.logger import bind_run_context, clear_observability_context, logger


async def resume_with_confirmation_impl(
    orchestrator,
    confirmation_id: str,
    approved: bool,
) -> AsyncIterator[str]:
    """Resume agent execution after tool confirmation."""
    state = await orchestrator.get_confirmation_state(confirmation_id)
    final_phase: AgentPhase = "cancelled"

    if not state:
        yield await orchestrator.stream_sse_event(
            SSEEventType.ERROR,
            ErrorEventData(
                code="confirmation_not_found",
                message="Confirmation not found or expired",
                recoverable=False,
            ).model_dump(),
            message_id="",
        )
        return

    if state.is_expired():
        yield await orchestrator.stream_sse_event(
            SSEEventType.ERROR,
            ErrorEventData(
                code="confirmation_expired",
                message="Confirmation expired",
                recoverable=False,
            ).model_dump(),
            message_id=state.message_id,
        )
        return

    if state.status != "pending":
        yield await orchestrator.stream_sse_event(
            SSEEventType.ERROR,
            ErrorEventData(
                code="confirmation_already_processed",
                message=f"Confirmation already {state.status}",
                recoverable=False,
            ).model_dump(),
            message_id=state.message_id,
        )
        return

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    processing_key = f"confirmation:{confirmation_id}:processing"
    acquired = await r.set(processing_key, "1", ex=orchestrator.CONFIRMATION_EXPIRY, nx=True)
    if not acquired:
        yield await orchestrator.stream_sse_event(
            SSEEventType.ERROR,
            ErrorEventData(
                code="confirmation_in_progress",
                message="Confirmation is already being processed",
                recoverable=True,
            ).model_dump(),
            message_id=state.message_id,
        )
        return

    try:
        status = "approved" if approved else "rejected"
        await orchestrator.update_confirmation_status(confirmation_id, status)

        runner, _, _, _ = orchestrator._initialize_agent_components()

        logger.info(
            "Agent resuming after confirmation",
            confirmation_id=confirmation_id,
            approved=approved,
            tool_name=state.tool_name,
            session_id=state.session_id,
        )

        tool_call_id = f"confirm_{confirmation_id}"
        if approved:
            yield await orchestrator.stream_sse_event(
                SSEEventType.TOOL_CALL,
                ToolCallEventData(
                    id=tool_call_id,
                    tool=state.tool_name,
                    label=orchestrator._get_tool_label(state.tool_name),
                    status="running",
                ).model_dump(),
                message_id=state.message_id,
            )

            try:
                result = await runner.resume_with_tool(
                    session_id=state.session_id,
                    tool_name=state.tool_name,
                    parameters=state.parameters,
                    confirmed=True,
                )

                success = bool(result.get("success", False))
                summary = orchestrator._build_tool_result_summary(
                    state.tool_name,
                    success,
                    result.get("data"),
                )
                yield await orchestrator.stream_sse_event(
                    SSEEventType.TOOL_RESULT,
                    ToolResultEventData(
                        id=tool_call_id,
                        tool=state.tool_name,
                        label=orchestrator._get_tool_label(state.tool_name),
                        status="success" if success else "failed",
                        summary=summary,
                    ).model_dump(),
                    message_id=state.message_id,
                )

                yield await orchestrator.stream_sse_event(
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
                yield await orchestrator.stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        code="tool_execution_failed",
                        message=str(e),
                        recoverable=False,
                    ).model_dump(),
                    message_id=state.message_id,
                )
                final_phase = "error"
        else:
            yield await orchestrator.stream_sse_event(
                "tool_rejected",
                {
                    "type": "tool_rejected",
                    "tool": state.tool_name,
                    "reason": "User rejected",
                    "message": f"Tool {state.tool_name} was rejected by user",
                },
                message_id=state.message_id,
            )

            yield await orchestrator.stream_sse_event(
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
        await r.delete(f"confirmation:{confirmation_id}")
        await r.delete(processing_key)
        orchestrator._close_message_binding(message_id=state.message_id, final_phase=final_phase)
        clear_observability_context()


async def execute_with_streaming_impl(
    orchestrator,
    user_input: str,
    session_id: str,
    user_id: str,
    auto_confirm: bool = False,
    mode: str = "auto",
    scope: Optional[Dict[str, Any]] = None,
    task_type: str = "general",
) -> AsyncIterator[str]:
    """Execute agent and stream SSE events."""
    run_id = str(uuid.uuid4())
    set_run_context(run_id=run_id, session_id=session_id)

    message_id = await orchestrator._create_assistant_message(
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

    runner, _, _, _ = orchestrator._initialize_agent_components()

    event_queue: Queue[Tuple[str, dict]] = Queue()
    event_counter = 0
    reasoning_seq = 0
    content_seq = 0
    accumulated_content = ""
    tool_registry: Dict[str, Dict[str, Any]] = {}

    event_id = f"{session_id}:{event_counter}"
    event_counter += 1
    yield await orchestrator.stream_sse_event_v2(
        SSEEventType.SESSION_START,
        SessionStartEventData(
            session_id=session_id,
            task_type=task_type,
            message_id=message_id,
        ).model_dump(),
        message_id=message_id,
        event_id=event_id,
    )

    current_phase: AgentPhase = "analyzing"
    event_id = f"{session_id}:{event_counter}"
    event_counter += 1
    yield await orchestrator.stream_sse_event_v2(
        SSEEventType.PHASE,
        PhaseEventData(
            phase="analyzing",
            label=orchestrator._get_phase_label("analyzing"),
        ).model_dump(),
        message_id=message_id,
        event_id=event_id,
    )

    async def event_callback(event_type: str, data: Dict[str, Any]):
        await event_queue.put((event_type, data))

    runner.event_callback = event_callback

    async def run_agent():
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

    try:
        while True:
            event_type, event_data = await event_queue.get()

            new_phase = orchestrator._infer_phase_from_event(
                event_type=event_type,
                event_data=event_data,
                previous_phase=current_phase,
            )

            if new_phase != current_phase and new_phase not in ("idle", "done", "error", "cancelled"):
                current_phase = new_phase
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.PHASE,
                    PhaseEventData(
                        phase=new_phase,
                        label=orchestrator._get_phase_label(new_phase),
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

            if event_type == "thought":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                reasoning_seq += 1
                content_chunk = event_data.get("content", "")
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.REASONING,
                    ReasoningEventData(
                        delta=content_chunk,
                        seq=reasoning_seq,
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

            elif event_type == "reasoning":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                reasoning_seq += 1
                content_chunk = event_data.get("content", "")
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.REASONING,
                    ReasoningEventData(
                        delta=content_chunk,
                        seq=reasoning_seq,
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

            elif event_type == "content":
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                content_seq += 1
                content_chunk = event_data.get("content", "")
                accumulated_content += content_chunk
                yield await orchestrator.stream_sse_event_v2(
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
                tool_registry[tool_id] = {
                    "tool": tool_name,
                    "parameters": tool_params,
                }

                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.TOOL_CALL,
                    ToolCallEventData(
                        id=tool_id,
                        tool=tool_name,
                        label=orchestrator._get_tool_label(tool_name),
                        status="running",
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

            elif event_type == "tool_result":
                tool_id = event_data.get("id", f"tool_{event_counter}")
                tool_name = event_data.get("tool")
                if not tool_name and tool_id in tool_registry:
                    tool_name = tool_registry[tool_id].get("tool")
                display_tool_name = tool_name or "tool"
                success = event_data.get("success", False)
                error_msg = event_data.get("error")
                data_summary = event_data.get("data")
                summary = orchestrator._build_tool_result_summary(tool_name, success, data_summary)

                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.TOOL_RESULT,
                    ToolResultEventData(
                        id=tool_id,
                        tool=display_tool_name,
                        label=orchestrator._get_tool_label(display_tool_name),
                        status="success" if success else "failed",
                        summary=summary,
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

                try:
                    await orchestrator._persist_tool_message(
                        session_id=session_id,
                        tool_id=tool_id,
                        tool_name=tool_name,
                        success=success,
                        error_msg=error_msg,
                        data_summary=data_summary,
                        tool_registry=tool_registry,
                    )
                except Exception as e:
                    logger.warning(
                        "Tool message persistence failed (non-blocking)",
                        session_id=session_id,
                        tool_id=tool_id,
                        error=str(e),
                    )

            elif event_type == "agent_complete":
                result = event_data

                if result.get("needs_confirmation"):
                    confirmation_state = await orchestrator.handle_confirmation_required(
                        session_id=session_id,
                        user_id=user_id,
                        message_id=message_id,
                        tool_name=result.get("tool_name", "unknown"),
                        parameters=result.get("tool_parameters", {}),
                    )

                    current_phase = "tool_calling"
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
                        SSEEventType.PHASE,
                        PhaseEventData(
                            phase="tool_calling",
                            label=orchestrator._get_phase_label("tool_calling"),
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
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
                    break

                if result.get("success"):
                    final_content = result.get("answer", accumulated_content)
                    if final_content != accumulated_content and not accumulated_content:
                        event_id = f"{session_id}:{event_counter}"
                        event_counter += 1
                        yield await orchestrator.stream_sse_event_v2(
                            SSEEventType.MESSAGE,
                            MessageEventData(
                                delta=final_content,
                                seq=0,
                            ).model_dump(),
                            message_id=message_id,
                            event_id=event_id,
                        )

                    await orchestrator._safe_update_assistant_message(message_id, final_content)

                    current_phase = "done"
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
                        SSEEventType.PHASE,
                        PhaseEventData(
                            phase="done",
                            label=orchestrator._get_phase_label("done"),
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
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
                else:
                    current_phase = "error"
                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
                        SSEEventType.PHASE,
                        PhaseEventData(
                            phase="error",
                            label=orchestrator._get_phase_label("error"),
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

                    event_id = f"{session_id}:{event_counter}"
                    event_counter += 1
                    yield await orchestrator.stream_sse_event_v2(
                        SSEEventType.ERROR,
                        ErrorEventData(
                            code="execution_failed",
                            message=result.get("error", "Unknown error"),
                            recoverable=False,
                        ).model_dump(),
                        message_id=message_id,
                        event_id=event_id,
                    )

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
                orchestrator._close_message_binding(message_id=message_id, final_phase=current_phase)
                break

            elif event_type == "agent_error":
                current_phase = "error"
                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.PHASE,
                    PhaseEventData(
                        phase="error",
                        label=orchestrator._get_phase_label("error"),
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

                event_id = f"{session_id}:{event_counter}"
                event_counter += 1
                yield await orchestrator.stream_sse_event_v2(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        code="agent_error",
                        message=event_data.get("error", "Unknown error"),
                        recoverable=True,
                    ).model_dump(),
                    message_id=message_id,
                    event_id=event_id,
                )

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
                orchestrator._close_message_binding(message_id=message_id, final_phase=current_phase)
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
