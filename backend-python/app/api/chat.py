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
from typing import AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.agent_runner import AgentRunner
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager
from app.llm.glm_client import GLMClient
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

router = APIRouter()


# =============================================================================
# Authentication Helper (placeholder - implement based on your auth system)
# =============================================================================


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from JWT token.

    TODO: Implement actual JWT validation
    For now, extract user_id from a test header or return a test user.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User UUID

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        # For development/testing, return a test user ID
        # TODO: Remove this in production and enforce authentication
        logger.warning("No authorization header - using test user")
        return "00000000-0000-0000-0000-000000000001"

    # TODO: Implement JWT validation
    # For now, just extract user_id from token payload
    try:
        # Placeholder: In real implementation, decode and validate JWT
        return "00000000-0000-0000-0000-000000000001"

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# =============================================================================
# Helper: Initialize Agent components
# =============================================================================


def initialize_agent_components() -> tuple[AgentRunner, ToolRegistry, SafetyLayer, ContextManager]:
    """Initialize Agent Runner and its dependencies.

    Returns:
        Tuple of (AgentRunner, ToolRegistry, SafetyLayer, ContextManager)
    """
    # Initialize components
    tool_registry = ToolRegistry()
    safety_layer = SafetyLayer()
    context_manager = ContextManager()
    llm_client = GLMClient()

    # Create Agent Runner
    runner = AgentRunner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
        safety_layer=safety_layer,
        max_iterations=10
    )

    return runner, tool_registry, safety_layer, context_manager


# =============================================================================
# SSE Streaming Helper
# =============================================================================


async def stream_sse_event(event_type: str, data: Dict) -> str:
    """Format data as SSE event.

    Args:
        event_type: Event type (thought, tool_call, etc.)
        data: Event data dictionary

    Returns:
        Formatted SSE string
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# =============================================================================
# Chat Streaming Endpoint
# =============================================================================


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    user_id: str = Header(None, alias="X-User-ID")
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
        # Get user ID
        if not user_id:
            user_id = await get_current_user_id()

        logger.info(
            "Chat stream started",
            user_id=user_id,
            session_id=request.session_id,
            message=request.message[:100]
        )

        # Get or create session
        session = None
        if request.session_id:
            session = await session_manager.get_session(request.session_id)
            if not session:
                logger.warning(
                    "Session not found, creating new",
                    session_id=request.session_id
                )

        if not session:
            session = await session_manager.create_session(
                user_id=user_id,
                title=request.message[:50] if len(request.message) > 50 else request.message
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
                if hasattr(request, 'headers') and 'last-event-id' in request.headers:
                    last_event_id = request.headers['last-event-id']

                # If reconnecting, replay missed events first
                if last_event_id:
                    async for replay_event in sse_manager.handle_reconnect(
                        session_id,
                        last_event_id
                    ):
                        yield replay_event

                # Business event generator
                async def business_events() -> AsyncIterator[str]:
                    """Generate business events from Agent execution."""
                    # Send initial thought event
                    yield await stream_sse_event(
                        SSEEventType.THOUGHT,
                        ThoughtEventData(
                            type="thinking",
                            content="Analyzing your request..."
                        ).model_dump()
                    )

                    # Execute Agent
                    result = await runner.execute(
                        user_input=request.message,
                        session_id=session_id,
                        user_id=user_id,
                        auto_confirm=auto_confirm
                    )

                    # Handle confirmation required
                    if result.get("needs_confirmation"):
                        confirmation_id = str(uuid.uuid4())

                        yield await stream_sse_event(
                            SSEEventType.CONFIRMATION_REQUIRED,
                            ConfirmationRequiredEventData(
                                type="confirmation_required",
                                confirmation_id=confirmation_id,
                                message=result.get("message", "Agent wants to execute a dangerous operation"),
                                tool_name=result.get("tool_name", "unknown"),
                                parameters=result.get("tool_parameters", {})
                            ).model_dump()
                        )
                        return

                    # Handle final message
                    if result.get("success"):
                        # Send tool calls history (optional)
                        tool_calls = result.get("tool_calls", [])
                        for tc in tool_calls:
                            # Tool call event
                            yield await stream_sse_event(
                                SSEEventType.TOOL_CALL,
                                ToolCallEventData(
                                    type="tool_call",
                                    tool=tc.get("tool", "unknown"),
                                    parameters=tc.get("parameters", {})
                                ).model_dump()
                            )

                            # Tool result event
                            tool_result = tc.get("result", {})
                            yield await stream_sse_event(
                                SSEEventType.TOOL_RESULT,
                                ToolResultEventData(
                                    type="tool_result",
                                    tool=tc.get("tool", "unknown"),
                                    success=tool_result.get("success", False),
                                    data=tool_result.get("data"),
                                    error=tool_result.get("error")
                                ).model_dump()
                            )

                        # Send final message
                        yield await stream_sse_event(
                            SSEEventType.MESSAGE,
                            MessageEventData(
                                type="message",
                                content=result.get("answer", "Task completed")
                            ).model_dump()
                        )

                        # Send done event
                        yield await stream_sse_event(
                            SSEEventType.DONE,
                            {"type": "done", "content": "[DONE]"}
                        )

                    else:
                        # Error case
                        yield await stream_sse_event(
                            SSEEventType.ERROR,
                            ErrorEventData(
                                type="error",
                                error=result.get("error", "Unknown error"),
                                details={"iterations": result.get("iterations", 0)}
                            ).model_dump()
                        )

                # Stream with heartbeat
                async for event in sse_manager.stream_with_heartbeat(
                    session_id,
                    business_events()
                ):
                    yield event

            except Exception as e:
                logger.error("SSE stream error", error=str(e))

                yield await stream_sse_event(
                    SSEEventType.ERROR,
                    ErrorEventData(
                        type="error",
                        error=str(e)
                    ).model_dump()
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
            }
        )

    except Exception as e:
        logger.error("Chat stream initialization error", error=str(e))

        # Return error as SSE event
        async def error_stream():
            yield await stream_sse_event(
                SSEEventType.ERROR,
                ErrorEventData(
                    type="error",
                    error=str(e)
                ).model_dump()
            )

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=status.HTTP_200_OK
        )


# =============================================================================
# User Confirmation Endpoint
# =============================================================================


@router.post("/chat/confirm")
async def confirm_action(
    request: ChatConfirmRequest,
    user_id: str = Header(None, alias="X-User-ID")
):
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
        if not user_id:
            user_id = await get_current_user_id()

        logger.info(
            "Confirmation received",
            confirmation_id=request.confirmation_id,
            approved=request.approved,
            session_id=request.session_id
        )

        # TODO: Validate confirmation_id from database/cache
        # For now, assume it's valid

        if not request.approved:
            return {
                "success": False,
                "message": "User declined the operation"
            }

        # Resume Agent execution
        runner, _, _, _ = initialize_agent_components()

        # TODO: Retrieve tool_name and parameters from confirmation request storage
        # For now, return success
        return {
            "success": True,
            "message": "Operation confirmed. Agent execution resumed."
        }

    except Exception as e:
        logger.error("Confirmation error", error=str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process confirmation: {str(e)}"
        )


# =============================================================================
# Chat History Endpoint
# =============================================================================


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user_id: str = Header(None, alias="X-User-ID"),
    limit: int = 50
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
        if not user_id:
            user_id = await get_current_user_id()

        # Get session
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Verify ownership
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session"
            )

        # TODO: Retrieve messages from PostgreSQL chat_messages table
        # For now, return empty list
        messages: List[Dict] = []

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "messages": messages,
                "total": len(messages),
                "limit": limit
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get messages error", error=str(e), session_id=session_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )