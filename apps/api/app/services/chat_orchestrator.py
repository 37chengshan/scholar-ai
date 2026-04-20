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
)
from app.models.confirmation import ConfirmationState
from app.services.message_service import message_service
from app.services.chat_orchestrator_runtime import (
    execute_with_streaming_impl,
    resume_with_confirmation_impl,
)
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
            count_towards_stats=False,
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
        updated = await message_service.update_message(
            message_id=message_id,
            content=content,
        )
        if not updated:
            logger.warning(
                "Assistant message update missed target",
                message_id=message_id,
            )
    
    async def _safe_update_assistant_message(
        self,
        message_id: str,
        content: str,
    ) -> None:
        """Best-effort assistant message update that never breaks streaming."""
        try:
            await self._update_assistant_message(message_id=message_id, content=content)
        except Exception as e:
            logger.warning(
                "Assistant message update failed (non-blocking)",
                message_id=message_id,
                error=str(e),
            )

    def _initialize_agent_components(self):
        """Resolve agent runtime dependencies through orchestrator boundary.

        Keeping initialization behind the orchestrator makes the runtime helper
        testable without patching a second module-level import site.
        """
        return initialize_agent_components()

    async def _persist_tool_message(
        self,
        session_id: str,
        tool_id: str,
        tool_name: str | None,
        success: bool,
        error_msg: str | None,
        data_summary: Any,
        tool_registry: Dict[str, Dict[str, Any]],
    ) -> None:
        """Persist a tool result message without leaking runtime dependencies.

        Tool message persistence is best-effort and must never break streaming.
        """
        tool_payload = {
            "id": tool_id,
            "tool": tool_name,
            "success": success,
            "error": error_msg,
            "data": data_summary,
        }

        await message_service.save_message(
            session_id=session_id,
            role="tool",
            content=json.dumps(tool_payload, ensure_ascii=False),
            tool_name=tool_name if tool_name and tool_name != "unknown" else None,
            tool_params=(
                tool_registry.get(tool_id, {}).get("parameters")
                if tool_id in tool_registry
                else None
            ),
        )

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
        async for event in resume_with_confirmation_impl(self, confirmation_id, approved):
            yield event

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
        async for event in execute_with_streaming_impl(
            orchestrator=self,
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            auto_confirm=auto_confirm,
            mode=mode,
            scope=scope,
            task_type=task_type,
        ):
            yield event

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
