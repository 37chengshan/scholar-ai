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

SSE Event Types:
- thought: Agent thinking process
- tool_call: Tool execution start
- tool_result: Tool execution result
- confirmation_required: Needs user approval
- message: Final response
- error: Error occurred
- done: Stream complete
"""

import json
import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
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
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest, http_request: Request, user_id: str = CurrentUserId
):
    """
    SSE streaming chat with Agent.

    Flow:
    1. Get or create session (SessionManager)
    2. Save user message (MessageService)
    3. Execute Agent with SSE streaming (ChatOrchestrator)
    4. Save tool call and assistant messages (MessageService)
    5. Handle confirmation requests (pause execution)

    SSE Events:
    - event: thought - Agent thinking process
    - event: tool_call - Tool execution start
    - event: tool_result - Tool execution result
    - event: confirmation_required - Needs user approval
    - event: message - Final response
    - event: error - Error occurred
    - event: done - Stream complete
    """
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

        auto_confirm = False
        if request.context:
            auto_confirm = request.context.get("auto_confirm", False)

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events from Agent execution with message persistence."""
            try:
                last_event_id = None
                if "last-event-id" in http_request.headers:
                    last_event_id = http_request.headers["last-event-id"]

                if last_event_id:
                    async for replay_event in sse_manager.handle_reconnect(
                        session_id, last_event_id
                    ):
                        yield replay_event

                async def business_events() -> AsyncIterator[str]:
                    """Generate business events with message persistence."""
                    try:
                        await message_service.save_message(
                            session_id=session_id,
                            role="user",
                            content=request.message,
                        )
                    except Exception as e:
                        logger.warning("Failed to save user message", error=str(e))

                    async for event in chat_orchestrator.execute_with_streaming(
                        user_input=request.message,
                        session_id=session_id,
                        user_id=user_id,
                        auto_confirm=auto_confirm,
                    ):
                        if event.startswith("event: tool_result"):
                            try:
                                data_start = event.find("data: ") + 6
                                data_json = event[data_start : event.rfind("\n")]
                                event_data = json.loads(data_json)

                                await message_service.save_message(
                                    session_id=session_id,
                                    role="tool",
                                    content=json.dumps(event_data),
                                    tool_name=event_data.get("tool", "unknown"),
                                    tool_params=event_data.get("parameters", {}),
                                )
                            except Exception as e:
                                logger.warning(
                                    "Failed to save tool message", error=str(e)
                                )

                        elif event.startswith("event: message"):
                            try:
                                data_start = event.find("data: ") + 6
                                data_json = event[data_start : event.rfind("\n")]
                                event_data = json.loads(data_json)

                                await message_service.save_message(
                                    session_id=session_id,
                                    role="assistant",
                                    content=event_data.get("content", ""),
                                )
                            except Exception as e:
                                logger.warning(
                                    "Failed to save assistant message", error=str(e)
                                )

                        yield event

                async for event in sse_manager.stream_with_heartbeat(
                    session_id, business_events()
                ):
                    yield event

            except Exception as e:
                logger.error("SSE stream error", error=str(e))
                yield await chat_orchestrator.stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        type="error", error=str(e), details=None
                    ).model_dump(),
                )

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

        async def error_stream():
            yield await chat_orchestrator.stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error", error=error_msg, details=None
                ).model_dump(),
            )

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
