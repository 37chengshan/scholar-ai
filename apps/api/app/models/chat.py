"""Chat API request/response models.

Defines schemas for:
- Chat streaming requests with session and context
- User confirmation requests for dangerous operations
- SSE event types and data structures (v2 with message_id binding)

HARD RULE 0.2: Each SSE event must bind to current assistant message ID.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatStreamRequest(BaseModel):
    """Request for chat streaming endpoint."""

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID (creates new session if None)",
    )
    message: str = Field(
        ...,
        description="User message",
        min_length=1,
        max_length=10000,
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (paper_ids, auto_confirm, etc.)",
    )


class ChatConfirmRequest(BaseModel):
    """Request for user confirmation endpoint."""

    confirmation_id: str = Field(
        ...,
        description="Unique confirmation ID",
    )
    approved: bool = Field(
        ...,
        description="Whether user approved the action",
    )
    session_id: str = Field(
        ...,
        description="Session ID to resume execution",
    )


# ============================================================
# SSE Event Types (v2 - 单流双通道 + message_id 绑定)
# ============================================================

# Phase types for Agent workflow
AgentPhase = Literal[
    "idle", "analyzing", "retrieving", "reading",
    "tool_calling", "synthesizing", "verifying",
    "done", "error", "cancelled"
]

# Task types for session
TaskType = Literal["single_paper", "kb_qa", "compare", "general"]


class SSEEventType:
    """Constants for SSE event types (v2).

    新增事件类型：
    - session_start: 会话开始
    - phase: 阶段切换
    - reasoning: 思考内容流（替代 thought）
    - message: 正文内容流
    - tool_call: 工具调用开始
    - tool_result: 工具调用结果
    - citation: 引用信息
    - routing_decision: 路由决策
    - confirmation_required: 需要用户确认
    - cancel: 用户取消
    - done: 流结束
    - error: 错误
    - heartbeat: 心跳
    """

    SESSION_START = "session_start"
    PHASE = "phase"
    REASONING = "reasoning"
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CITATION = "citation"
    ROUTING_DECISION = "routing_decision"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CANCEL = "cancel"
    DONE = "done"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

    # Legacy aliases (for backward compatibility)
    THOUGHT = "thought"  # Alias for reasoning


class SSEEventEnvelope(BaseModel):
    """SSE 事件信封结构 - 强制 message_id 绑定 (HARD RULE 0.2).

    每个事件都必须带 message_id，防止快速连续发送时串流。
    """

    event: str = Field(
        ...,
        description="Event type",
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event data payload",
    )
    message_id: str = Field(
        ...,
        description="Bound assistant message ID (HARD RULE 0.2)",
    )


class SSEEvent(BaseModel):
    """Server-Sent Event structure (legacy - use SSEEventEnvelope)."""

    event: str = Field(
        ...,
        description="Event type (thought, tool_call, tool_result, message, etc.)",
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event data payload",
    )


# ============================================================
# SSE Event Data Structures (v2)
# ============================================================

class SessionStartEventData(BaseModel):
    """Data for 'session_start' SSE event."""

    session_id: str = Field(..., description="Session ID")
    task_type: TaskType = Field(..., description="Task type")
    message_id: str = Field(..., description="Created assistant message ID")


class PhaseEventData(BaseModel):
    """Data for 'phase' SSE event."""

    phase: AgentPhase = Field(..., description="Current phase")
    label: str = Field(..., description="User-friendly label (e.g., '分析问题中')")


class ReasoningEventData(BaseModel):
    """Data for 'reasoning' SSE event."""

    delta: str = Field(..., description="Reasoning chunk content")
    seq: int = Field(default=0, description="Sequence number")


class MessageEventData(BaseModel):
    """Data for 'message' SSE event."""

    delta: str = Field(..., description="Message chunk content")
    seq: int = Field(default=0, description="Sequence number")


class ToolCallEventData(BaseModel):
    """Data for 'tool_call' SSE event (v2)."""

    id: str = Field(..., description="Tool call ID (e.g., 'tool_1')")
    tool: str = Field(..., description="Tool name (e.g., 'rag_search')")
    label: str = Field(..., description="User-friendly label (e.g., '检索知识库')")
    status: Literal["running"] = Field(default="running", description="Tool status")


class ToolResultEventData(BaseModel):
    """Data for 'tool_result' SSE event (v2)."""

    id: str = Field(..., description="Tool call ID")
    tool: str = Field(..., description="Tool name")
    label: str = Field(..., description="User-friendly label")
    status: Literal["success", "failed"] = Field(..., description="Execution status")
    summary: Optional[str] = Field(None, description="Result summary (e.g., '命中 3 篇论文')")


class CitationEventData(BaseModel):
    """Data for 'citation' SSE event."""

    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    pages: List[int] = Field(default_factory=list, description="Referenced pages")
    hits: int = Field(default=0, description="Number of hits")


class RoutingDecisionEventData(BaseModel):
    """Data for 'routing_decision' SSE event."""

    decision: str = Field(..., description="Routing decision (simple/complex/agent)")
    reason: str = Field(..., description="Routing reason")


class CancelEventData(BaseModel):
    """Data for 'cancel' SSE event."""

    reason: Literal["user_stop", "timeout", "network_error"] = Field(
        ..., description="Cancel reason"
    )


class DoneEventData(BaseModel):
    """Data for 'done' SSE event."""

    finish_reason: Literal["stop", "tool_calls", "length", "cancel"] = Field(
        ..., description="Finish reason"
    )
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    cost: Optional[float] = Field(None, description="Estimated cost")
    total_time_ms: Optional[int] = Field(None, description="Total execution time")


class ErrorEventData(BaseModel):
    """Data for 'error' SSE event."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    recoverable: bool = Field(default=False, description="Whether error is recoverable")


class ConfirmationRequiredEventData(BaseModel):
    """Data for 'confirmation_required' SSE event."""

    confirmation_id: str = Field(..., description="Unique confirmation ID")
    message: str = Field(..., description="Confirmation message for user")
    tool_name: str = Field(..., description="Tool requiring confirmation")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


# ============================================================
# Legacy Event Data Structures (for backward compatibility)
# ============================================================

class ThoughtEventData(BaseModel):
    """Data for 'thought' SSE event (legacy - use ReasoningEventData)."""

    type: str = Field(default="thinking", description="Thought type")
    content: str = Field(..., description="Thought content")