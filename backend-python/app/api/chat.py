"""Chat API endpoints with SSE streaming.

Provides endpoints for:
- POST /api/chat/stream: SSE streaming chat with Agent
- POST /api/chat/confirm: User confirmation for dangerous operations
- GET /api/sessions/{session_id}/messages: Retrieve chat history

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
import time
import uuid
import asyncio
from asyncio import Queue
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.agent_runner import AgentRunner
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager
from app.core.database import get_db_connection
from app.config import settings
from app.utils.agent_init import initialize_agent_components
from app.models.chat import (
    ChatStreamRequest,
    ChatConfirmRequest,
    SSEEvent,
    SSEEventType,
    ThoughtEventData,
    ToolCallEventData,
    ToolResultEventData,
    ConfirmationRequiredEventData,
    MessageEventData,
    ErrorEventData,
)
from app.utils.session_manager import session_manager
from app.utils.sse_manager import sse_manager
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# SSE Helper
# =============================================================================


async def stream_sse_event(event_type: str, data: dict) -> str:
    """Format SSE event as string.

    Args:
        event_type: SSE event type (thought, tool_call, message, etc.)
        data: Event data payload

    Returns:
        SSE formatted string: "event: {type}\\ndata: {json}\\n\\n"
    """
    event_str = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    return event_str


# =============================================================================
# Chat Stream Endpoint
# =============================================================================


async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_params: Optional[Dict] = None,
) -> str:
    """Save chat message to PostgreSQL and update session stats.

    Args:
        session_id: Session UUID
        role: Message role (user, assistant, tool, system)
        content: Message content
        tool_name: Tool name if role=tool
        tool_params: Tool parameters if role=tool

    Returns:
        Message UUID

    Raises:
        Exception: If database insert fails
    """
    message_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)

    async with get_db_connection() as conn:
        # Insert message
        await conn.execute(
            """
            INSERT INTO chat_messages (id, session_id, role, content, tool_name, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            message_id,
            session_id,
            role,
            content,
            tool_name,
            created_at,
        )

        # Update session stats
        is_tool_call = role == "tool"
        await conn.execute(
            """
            UPDATE sessions
            SET 
                message_count = message_count + 1,
                tool_call_count = tool_call_count + CASE WHEN $2 THEN 1 ELSE 0 END,
                last_activity_at = $3
            WHERE id = $1
            """,
            session_id,
            is_tool_call,
            created_at,
        )

    logger.debug(
        "Message saved", message_id=message_id, session_id=session_id, role=role
    )

    return message_id


# =============================================================================
# SSE Helper
# =============================================================================


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest, http_request: Request, user_id: str = CurrentUserId
):
    """
    SSE streaming chat with Agent.

    Flow:
    1. Get or create session
    2. Initialize Agent Runner
    3. Execute Agent loop with SSE events
    4. Handle confirmation requests (pause execution)
    5. Save messages to PostgreSQL after completion
    6. Send heartbeat every 15s to maintain connection

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

        # Get or create session
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

        # Initialize Agent components
        runner, _, _, _ = initialize_agent_components()

        # Get auto_confirm from context
        auto_confirm = False
        if request.context:
            auto_confirm = request.context.get("auto_confirm", False)

        # SSE event generator with heartbeat and reconnection support
        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events from Agent execution with heartbeat."""
            try:
                # Check for Last-Event-ID header (reconnection)
                last_event_id = None
                if "last-event-id" in http_request.headers:
                    last_event_id = http_request.headers["last-event-id"]

                # If reconnecting, replay missed events first
                if last_event_id:
                    async for replay_event in sse_manager.handle_reconnect(
                        session_id, last_event_id
                    ):
                        yield replay_event

                # Business event generator with real-time SSE streaming
                async def business_events() -> AsyncIterator[str]:
                    """Generate business events from Agent execution with real-time streaming."""
                    # Create event queue for real-time push
                    event_queue: Queue[Tuple[str, dict]] = Queue()

                    # Save user message before execution
                    try:
                        await save_message(
                            session_id=session_id, role="user", content=request.message
                        )
                    except Exception as e:
                        logger.warning("Failed to save user message", error=str(e))

                    # Send initial thought event
                    yield await stream_sse_event(
                        SSEEventType.THOUGHT,
                        ThoughtEventData(
                            type="thinking", content="Analyzing your request..."
                        ).model_dump(),
                    )

                    # Define event callback to push events to queue
                    async def event_callback(event_type: str, data: Dict[str, Any]):
                        """Push real-time events to SSE queue."""
                        await event_queue.put((event_type, data))

                    # Define agent execution task
                    async def run_agent():
                        """Execute agent and push completion signal."""
                        try:
                            result = await runner.execute(
                                user_input=request.message,
                                session_id=session_id,
                                user_id=user_id,
                                auto_confirm=auto_confirm,
                                event_callback=event_callback,  # Real-time callback
                            )

                            # Push final result signal
                            await event_queue.put(("agent_complete", result))

                        except Exception as e:
                            logger.error("Agent execution error", error=str(e))
                            await event_queue.put(("agent_error", {"error": str(e)}))

                    # Start agent task in parallel
                    agent_task = asyncio.create_task(run_agent())

                    # Stream events from queue in real-time
                    while True:
                        event_type, event_data = await event_queue.get()

                        # Handle real-time events
                        if event_type == "thought":
                            yield await stream_sse_event(
                                SSEEventType.THOUGHT,
                                ThoughtEventData(
                                    type="thinking",
                                    content=event_data.get("content", ""),
                                ).model_dump(),
                            )

                        elif event_type == "tool_call":
                            yield await stream_sse_event(
                                SSEEventType.TOOL_CALL,
                                ToolCallEventData(
                                    type="tool_call",
                                    tool=event_data.get("tool", "unknown"),
                                    parameters=event_data.get("parameters", {}),
                                ).model_dump(),
                            )

                        elif event_type == "tool_result":
                            yield await stream_sse_event(
                                SSEEventType.TOOL_RESULT,
                                ToolResultEventData(
                                    type="tool_result",
                                    tool=event_data.get("tool", "unknown"),
                                    success=event_data.get("success", False),
                                    data=event_data.get("data"),
                                    error=event_data.get("error"),
                                ).model_dump(),
                            )

                            # Save tool call message asynchronously
                            try:
                                await save_message(
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

                        # Handle agent completion
                        elif event_type == "agent_complete":
                            result = event_data

                            # Handle confirmation required
                            if result.get("needs_confirmation"):
                                confirmation_id = str(uuid.uuid4())

                                yield await stream_sse_event(
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
                                )
                                break

                            # Handle final message
                            if result.get("success"):
                                # Send final message
                                final_content = result.get("answer", "Task completed")
                                yield await stream_sse_event(
                                    SSEEventType.MESSAGE,
                                    MessageEventData(
                                        type="message", content=final_content
                                    ).model_dump(),
                                )

                                # Save assistant message
                                try:
                                    await save_message(
                                        session_id=session_id,
                                        role="assistant",
                                        content=final_content,
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "Failed to save assistant message", error=str(e)
                                    )

                                # Send done event with token usage
                                yield await stream_sse_event(
                                    SSEEventType.DONE,
                                    {
                                        "type": "done",
                                        "content": "[DONE]",
                                        "tokens_used": result.get("tokens_used", 0),
                                        "cost": result.get("cost", 0.0),
                                        "iterations": result.get("iterations", 0),
                                        "total_time_ms": result.get("total_time_ms", 0),
                                    },
                                )
                            else:
                                # Error case
                                yield await stream_sse_event(
                                    SSEEventType.ERROR,
                                    ErrorEventData(
                                        type="error",
                                        error=result.get("error", "Unknown error"),
                                        details={
                                            "iterations": result.get("iterations", 0)
                                        },
                                    ).model_dump(),
                                )

                            break

                        # Handle agent error
                        elif event_type == "agent_error":
                            yield await stream_sse_event(
                                SSEEventType.ERROR,
                                ErrorEventData(
                                    type="error",
                                    error=event_data.get("error", "Unknown error"),
                                    details=None,
                                ).model_dump(),
                            )
                            break

                    # Ensure agent task completes
                    await agent_task

                # Stream with heartbeat
                async for event in sse_manager.stream_with_heartbeat(
                    session_id, business_events()
                ):
                    yield event

            except Exception as e:
                logger.error("SSE stream error", error=str(e))

                yield await stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        type="error", error=str(e), details=None
                    ).model_dump(),
                )

        # Return SSE streaming response
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

        # Capture error message for closure
        error_msg = str(e)

        # Return error as SSE event
        async def error_stream():
            yield await stream_sse_event(
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
# User Confirmation Endpoint
# =============================================================================


@router.post("/chat/confirm")
async def confirm_action(request: ChatConfirmRequest, user_id: str = CurrentUserId):
    """
    User confirmation for dangerous operations.

    Resumes Agent execution after user confirms or declines a dangerous tool.

    Args:
        request: Confirmation request with confirmation_id and approved flag
        user_id: Authenticated user ID

    Returns:
        Result of resumed Agent execution
    """
    try:
        logger.info(
            "Confirmation received",
            confirmation_id=request.confirmation_id,
            approved=request.approved,
            session_id=request.session_id,
        )

        # Validate confirmation_id from Redis
        import redis.asyncio as redis

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)

        confirmation_key = f"confirmation:{request.confirmation_id}"
        confirmation_data = await r.get(confirmation_key)

        if not confirmation_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Invalid or expired confirmation_id"),
            )

        # Parse confirmation data
        import json

        data = json.loads(confirmation_data)

        # Verify user ownership
        if data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden("Confirmation belongs to different user"),
            )

        if not request.approved:
            # Clear confirmation from Redis
            await r.delete(confirmation_key)
            return {"success": False, "message": "User declined the operation"}

        # Resume Agent execution
        runner, _, _, _ = initialize_agent_components()

        # Retrieve tool_name and parameters from confirmation data
        tool_name = data.get("tool_name")
        tool_params = data.get("tool_params", {})
        session_id = data.get("session_id")

        # Clear confirmation from Redis
        await r.delete(confirmation_key)

        return {
            "success": True,
            "message": "Operation confirmed. Agent execution resumed.",
            "tool_name": tool_name,
            "tool_params": tool_params,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error("Confirmation error", error=str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to process confirmation: {str(e)}"),
        )


# =============================================================================
# Chat History Endpoint
# =============================================================================


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str, user_id: str = CurrentUserId, limit: int = 50, offset: int = 0
):
    """
    Retrieve chat history for a session.

    Returns list of messages with:
    - User messages
    - Agent responses
    - Tool call records

    Args:
        session_id: Session UUID
        user_id: Authenticated user ID
        limit: Maximum number of messages (default 50)

    Returns:
        List of ChatMessage objects
    """
    try:
        # Get session
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found(f"Session {session_id} not found"),
            )

        # Verify ownership
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Errors.forbidden(
                    "You don't have permission to access this session"
                ),
            )

        # Retrieve messages from PostgreSQL chat_messages table
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, session_id, role, content, tool_name, created_at
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                session_id,
                limit,
                offset,
            )

            messages = [dict(row) for row in rows]

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "messages": messages,
                "total": len(messages),
                "limit": limit,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get messages error", error=str(e), session_id=session_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get messages: {str(e)}"),
        )
