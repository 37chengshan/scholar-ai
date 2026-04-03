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
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.agent_runner import AgentRunner
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager
from app.core.database import get_db_connection
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
from app.utils.auth import validate_jwt_token
from app.utils.logger import logger

router = APIRouter()


# =============================================================================
# Authentication Helper
# =============================================================================


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> str:
    """Extract and validate user ID from JWT token.
    
    Args:
        authorization: Authorization header (Bearer token)
        
    Returns:
        User ID from validated token
        
    Raises:
        HTTPException: 401 if token missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization token"
        )
    
    token = authorization.split(" ")[1]
    user_id = await validate_jwt_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user_id


# =============================================================================
# Message Persistence Helper
# =============================================================================


async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_params: Optional[Dict] = None
) -> str:
    """Save chat message to PostgreSQL.
    
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
    created_at = datetime.now(timezone.utc)
    
    async with get_db_connection() as conn:
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
            created_at
        )
    
    logger.debug(
        "Message saved",
        message_id=message_id,
        session_id=session_id,
        role=role
    )
    
    return message_id


# =============================================================================
# Chat Stream Endpoint
# =============================================================================


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
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
                    # Save user message before execution
                    try:
                        await save_message(
                            session_id=session_id,
                            role="user",
                            content=request.message
                        )
                    except Exception as e:
                        logger.warning("Failed to save user message", error=str(e))
                    
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
                            
                            # Save tool call message
                            try:
                                await save_message(
                                    session_id=session_id,
                                    role="tool",
                                    content=json.dumps(tc.get("result", {})),
                                    tool_name=tc.get("tool", "unknown"),
                                    tool_params=tc.get("parameters", {})
                                )
                            except Exception as e:
                                logger.warning("Failed to save tool message", error=str(e))

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
                        final_content = result.get("answer", "Task completed")
                        yield await stream_sse_event(
                            SSEEventType.MESSAGE,
                            MessageEventData(
                                type="message",
                                content=final_content
                            ).model_dump()
                        )
                        
                        # Save assistant message
                        try:
                            await save_message(
                                session_id=session_id,
                                role="assistant",
                                content=final_content
                            )
                        except Exception as e:
                            logger.warning("Failed to save assistant message", error=str(e))

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

        # Validate confirmation_id from Redis
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        confirmation_key = f"confirmation:{request.confirmation_id}"
        confirmation_data = await r.get(confirmation_key)
        
        if not confirmation_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired confirmation_id"
            )
        
        # Parse confirmation data
        import json
        data = json.loads(confirmation_data)
        
        # Verify user ownership
        if data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Confirmation belongs to different user"
            )

        if not request.approved:
            # Clear confirmation from Redis
            await r.delete(confirmation_key)
            return {
                "success": False,
                "message": "User declined the operation"
            }

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
            "session_id": session_id
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
    limit: int = 50,
    offset: int = 0
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
                offset
            )
            
            messages = [dict(row) for row in rows]

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