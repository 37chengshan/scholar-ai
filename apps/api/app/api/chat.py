"""Chat API endpoints with SSE streaming.

Provides endpoints for:
- POST /api/v1/chat/stream: SSE streaming chat with Agent
- POST /api/v1/chat/confirm: User confirmation for dangerous operations

Note: Session messages endpoint moved to session.py:
- GET /api/v1/sessions/{session_id}/messages: Retrieve chat history

Per D-07: API layer handles request validation and response formatting.
Business logic is delegated to:
- MessageService: Message persistence
- ChatOrchestrator: Agent execution and SSE streaming
- SessionManager: Session CRUD
- ComplexityRouter: Dual-layer query routing (Task 1.4)
- SSEEventBuffer: Ordered event transmission (Task 1.4)

SSE Event Types:
- routing_decision: Query routing result (Task 1.4, first event)
- reasoning: Agent reasoning stream
- tool_call: Tool execution start
- tool_result: Tool execution result
- confirmation_required: Needs user approval
- message: Final response
- error: Error occurred
- done: Stream complete (MUST follow error events per P2)
"""

import json
from typing import Any, AsyncIterator, Dict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatStreamRequest,
    ChatConfirmRequest,
    SSEEventType,
    ErrorEventData,
)
from app.services.message_service import message_service
from app.services.chat_orchestrator import chat_orchestrator
from app.utils.session_manager import session_manager
from app.utils.sse_manager import sse_manager
from app.utils.logger import logger
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors

# Task 1.4: Import new modules for dual-layer routing
from app.core.complexity_router import ComplexityRouter
from app.core.sse_event_buffer import SSEEventBuffer

router = APIRouter()

# Task 1.4: Initialize ComplexityRouter (rule-based, no LLM client for now)
complexity_router = ComplexityRouter()


@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest, http_request: Request, user_id: str = CurrentUserId
):
    """
    SSE streaming chat with Agent.

    Task 1.4: Integrated dual-layer routing mechanism.

    Flow:
    1. Get or create session (SessionManager)
    2. Route query complexity (ComplexityRouter) - NEW
    3. Send routing_decision event (SSEEventBuffer) - NEW
    4. Save user message (MessageService)
    5. Execute Agent/RAG based on routing (ChatOrchestrator)
    6. Save tool call and assistant messages (MessageService)
    7. Handle confirmation requests (pause execution)

    SSE Events (Task 1.4 minimum loop):
    - event: routing_decision - Query routing result (FIRST event)
    - event: reasoning - Agent reasoning stream
    - event: message - Final response
    - event: done - Stream complete
    - event: error - Error occurred (MUST follow with done per P2)

    Additional events:
    - event: tool_call - Tool execution start
    - event: tool_result - Tool execution result
    - event: confirmation_required - Needs user approval
    """
    session_id = request.session_id or "unknown-session"

    try:
        logger.info(
            "Chat stream started",
            user_id=user_id,
            session_id=request.session_id,
            message=request.message[:100],
        )

        session = None
        if request.session_id:
            session = await session_manager.get_session(request.session_id)
            if not session:
                logger.warning(
                    "Session not found, creating new", session_id=request.session_id
                )

        if not session:
            session = await session_manager.create_session(
                user_id=user_id,
                title=request.message[:50]
                if len(request.message) > 50
                else request.message,
            )

        session_id = session.id

        # Task 1.4: Create SSEEventBuffer for ordered events
        event_buffer = SSEEventBuffer(session_id=session_id)

        def _normalize_sse_payload(
            event_type: str,
            raw_payload: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Normalize nested SSE envelope payload to flat event data.

            chat_orchestrator.stream_sse_event_v2 emits payload as:
            {"event": str, "data": {...}, "message_id": str}
            This gateway must flatten it so frontend receives fields like
            {"delta": "...", "message_id": "..."}.
            """
            if not isinstance(raw_payload, dict):
                return {"content": raw_payload}

            # New orchestrator envelope format
            if "data" in raw_payload and "message_id" in raw_payload:
                inner_data = raw_payload.get("data")
                normalized = (
                    dict(inner_data) if isinstance(inner_data, dict) else {"content": inner_data}
                )
                normalized["message_id"] = raw_payload.get("message_id")
                return normalized

            # Legacy flat payload format
            return dict(raw_payload)

        auto_confirm = False
        if request.context:
            auto_confirm = request.context.get("auto_confirm", False)

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events from Agent execution with message persistence.

            Task 1.4: Added routing_decision event at start.
            P2: Ensure error events are followed by done events.
            """
            try:
                last_event_id = http_request.headers.get("last-event-id")
                current_message_id = ""

                # Reconnect requests are replay-only. They must never restart business execution,
                # otherwise one user turn can be persisted/executed twice.
                if last_event_id:
                    logger.info(
                        "Reconnect stream detected, entering replay-only mode",
                        session_id=session_id,
                        last_event_id=last_event_id,
                    )

                    replayed_events = 0
                    replay_has_terminal = False

                    async for replay_event in sse_manager.handle_reconnect(
                        session_id, last_event_id
                    ):
                        replayed_events += 1
                        if "event: done" in replay_event or "event: error" in replay_event:
                            replay_has_terminal = True
                        yield replay_event

                    if replayed_events == 0:
                        error_event = await event_buffer.emit(
                            SSEEventType.ERROR,
                            ErrorEventData(
                                code="REPLAY_NOT_FOUND",
                                message=f"No replayable events found for Last-Event-ID: {last_event_id}",
                                recoverable=False,
                            ).model_dump()
                            | {"message_id": f"{session_id}:replay"},
                        )
                        yield error_event.to_sse_format()

                    if not replay_has_terminal:
                        done_event = await event_buffer.emit(
                            SSEEventType.DONE,
                            {
                                "status": "replay_complete",
                                "message_id": current_message_id or f"{session_id}:replay",
                            },
                        )
                        yield done_event.to_sse_format()

                    return

                # Task 1.4: Route query complexity (async with LLM fallback)
                routing_result = await complexity_router.route_async(request.message)

                logger.info(
                    "Query routed",
                    complexity=routing_result["complexity"],
                    method=routing_result["method"],
                    confidence=routing_result["confidence"],
                )

                # routing_decision must carry message_id (HARD RULE 0.2), so emit it
                # only after session_start establishes the bound assistant message.
                routing_emitted = False

                async def business_events() -> AsyncIterator[str]:
                    """Generate business events with message persistence.

                    Task 1.4: Routing determines execution path:
                    - simple → RAG mode (reasoning → message → done)
                    - complex → Agent mode (multi-step, simplified for MVP)
                    """
                    nonlocal routing_emitted
                    try:
                        await message_service.save_message(
                            session_id=session_id,
                            role="user",
                            content=request.message,
                        )
                    except Exception as e:
                        logger.warning("Failed to save user message", error=str(e))

                    # Task 1.4: Branch based on routing result
                    # Note: For MVP, both paths use chat_orchestrator
                    # Future: Simple queries → dedicated RAG path (simplified for now)

                    async for event in chat_orchestrator.execute_with_streaming(
                        user_input=request.message,
                        session_id=session_id,
                        user_id=user_id,
                        auto_confirm=auto_confirm,
                        mode=request.mode,
                        scope=request.scope,
                    ):
                        # Buffer events for ordered transmission
                        if event.startswith("event:"):
                            # Parse event type
                            event_type_line = event.split("\n")[0]
                            event_type = event_type_line.replace("event: ", "").strip()

                            # Parse event data
                            if "data: " in event:
                                data_start = event.find("data: ") + 6
                                data_json = event[data_start : event.rfind("\n")]
                                try:
                                    event_data = json.loads(data_json)
                                    normalized_payload = _normalize_sse_payload(
                                        event_type,
                                        event_data,
                                    )

                                    # Buffer normalized event payload
                                    buffered_event = await event_buffer.emit(
                                        event_type,
                                        normalized_payload,
                                    )
                                    yield buffered_event.to_sse_format()

                                    if (
                                        event_type == "session_start"
                                        and normalized_payload.get("message_id")
                                    ):
                                        current_message_id = str(normalized_payload.get("message_id"))

                                    # Emit routing_decision once message binding is available.
                                    if (
                                        event_type == "session_start"
                                        and not routing_emitted
                                        and normalized_payload.get("message_id")
                                    ):
                                        routing_event = await event_buffer.emit(
                                            "routing_decision",
                                            {
                                                "complexity": routing_result["complexity"],
                                                "method": routing_result["method"],
                                                "confidence": routing_result["confidence"],
                                                "reasoning": routing_result.get("reasoning", ""),
                                                "query_preview": request.message[:100],
                                                "message_id": normalized_payload.get("message_id"),
                                            },
                                        )
                                        yield routing_event.to_sse_format()
                                        routing_emitted = True
                                except json.JSONDecodeError:
                                    # Fallback to original event if parsing fails
                                    yield event
                            else:
                                yield event
                        else:
                            yield event

                async for event in sse_manager.stream_with_heartbeat(
                    session_id, business_events()
                ):
                    yield event

            except Exception as e:
                logger.error("SSE stream error", error=str(e))

                # P2: Send error event followed by done event (critical for frontend)
                error_event = await event_buffer.emit(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        code="STREAM_ERROR",
                        message=str(e),
                        recoverable=False,
                    ).model_dump()
                    | {"message_id": current_message_id or f"{session_id}:stream_error"},
                )
                yield error_event.to_sse_format()

                # P2: MUST send done event after error (frontend otherwise hangs)
                done_event = await event_buffer.emit(
                    SSEEventType.DONE,
                    {
                        "status": "error_terminated",
                        "message_id": current_message_id or f"{session_id}:stream_error",
                    },
                )
                yield done_event.to_sse_format()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Session-ID": session_id,
            },
        )

    except Exception as e:
        logger.error("Chat stream initialization error", error=str(e))
        error_msg = str(e)

        # P2: Error stream must also send done after error
        async def error_stream():
            # Create temporary buffer for error scenario
            temp_buffer = SSEEventBuffer(session_id="error")

            error_event = await temp_buffer.emit(
                SSEEventType.ERROR,
                ErrorEventData(
                    code="STREAM_INIT_ERROR",
                    message=error_msg,
                    recoverable=False,
                ).model_dump()
                | {"message_id": f"{session_id}:init_error"},
            )
            yield error_event.to_sse_format()

            # P2: MUST send done after error
            done_event = await temp_buffer.emit(
                SSEEventType.DONE,
                {
                    "status": "init_error",
                    "message_id": f"{session_id}:init_error",
                },
            )
            yield done_event.to_sse_format()

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=status.HTTP_200_OK,
        )


# =============================================================================
# User Confirmation Endpoint (Sprint 3: SSE Stream Response)
# =============================================================================


@router.post("/confirm")
async def confirm_action(
    request: ChatConfirmRequest,
    http_request: Request,
    user_id: str = CurrentUserId,
):
    """
    User confirmation for dangerous operations with SSE streaming.

    Sprint 3: Returns SSE stream with tool execution events for resumption.

    Args:
        request: Confirmation request with confirmation_id and approved flag
        http_request: HTTP request for headers
        user_id: Authenticated user ID

    Returns:
        SSE stream with tool execution and continuation events
    """
    try:
        logger.info(
            "Confirmation received",
            confirmation_id=request.confirmation_id,
            approved=request.approved,
            session_id=request.session_id,
            user_id=user_id,
        )

        # Get confirmation state from orchestrator
        confirmation_state = await chat_orchestrator.get_confirmation_state(
            request.confirmation_id
        )

        if not confirmation_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Invalid or expired confirmation_id"),
            )

        # Verify user ownership
        if confirmation_state.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden("Confirmation belongs to different user"),
            )

        # Verify session_id matches
        if confirmation_state.session_id != request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Session ID mismatch"),
            )

        # Generate SSE stream for resumption
        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events from Agent resumption."""
            async for event in chat_orchestrator.resume_with_confirmation(
                confirmation_id=request.confirmation_id,
                approved=request.approved,
            ):
                yield event

        # Wrap with heartbeat
        async def stream_with_heartbeat() -> AsyncIterator[str]:
            """Add heartbeat to SSE stream."""
            async for event in sse_manager.stream_with_heartbeat(
                request.session_id, event_generator()
            ):
                yield event

        logger.info(
            "Confirmation validated, streaming resumption events",
            confirmation_id=request.confirmation_id,
            approved=request.approved,
        )

        return StreamingResponse(
            stream_with_heartbeat(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Confirmation-Processed": "true",
            },
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise

    except Exception as e:
        logger.error("Confirmation processing error", error=str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to process confirmation: {str(e)}"),
        )


# ============================================================
# POST /api/v1/chat/cancel — Cancel a running agent
# ============================================================


@router.post("/cancel")
async def cancel_run(
    request: Request,
    user_id: str = CurrentUserId,
) -> Dict[str, Any]:
    """Cancel an active chat run.

    Per 战役 B WP7: Cancel is a system-level capability.
    """
    body = await request.json()
    session_id = body.get("session_id")
    run_id = body.get("run_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )

    logger.info(
        "Run cancel requested",
        session_id=session_id,
        run_id=run_id,
        user_id=user_id,
    )

    # Disconnect active SSE for this session
    sse_manager.disconnect(session_id)

    return {
        "status": "cancelled",
        "session_id": session_id,
        "run_id": run_id,
    }


# ============================================================
# POST /api/v1/chat/retry — Retry a failed run
# ============================================================


@router.post("/retry")
async def retry_run(
    request: Request,
    user_id: str = CurrentUserId,
) -> StreamingResponse:
    """Retry the last failed message in a session.

    Per 战役 B WP7: Retry is a system-level capability.
    Re-sends the last user message to create a new run.
    """
    body = await request.json()
    session_id = body.get("session_id")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )

    # Get last user message from session
    messages = await message_service.get_messages(
        session_id=session_id,
        limit=10,
    )

    last_user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg
            break

    if not last_user_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user message found to retry",
        )

    # Re-create a stream request with the last user message
    retry_request = ChatStreamRequest(
        session_id=session_id,
        message=last_user_msg["content"],
        mode=body.get("mode", "auto"),
        scope=body.get("scope"),
    )

    logger.info(
        "Retrying last message",
        session_id=session_id,
        message_preview=last_user_msg["content"][:100],
    )

    # Delegate to the stream endpoint logic
    return await chat_stream(
        request=retry_request,
        http_request=request,
        user_id=user_id,
    )
