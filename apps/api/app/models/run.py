"""Agent Run / Step / ToolEvent / Artifact models.

Defines the core Agent-Native runtime contract:
- Run: top-level execution unit
- RunPhase: lifecycle phases with deterministic transitions
- RunStep: ordered execution step within a run
- ToolEvent: tool call/result within a step
- RunArtifact: generated output artifacts
- RunEvidence: citation and evidence binding
- FinalSummary: structured answer with evidence

Per 战役 B WP5: Run / Step / ToolEvent contract.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# Run Phase State Machine
# ============================================================

class RunPhase(str, Enum):
    """Agent run lifecycle phases.

    State transitions:
        idle -> planning -> executing -> verifying -> completed
                    |            |            |
                    v            v            v
              waiting_for_user  failed    cancelled
                    |
                    v
               executing (resume)
    """

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_FOR_USER = "waiting_for_user"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid phase transitions
PHASE_TRANSITIONS: Dict[RunPhase, List[RunPhase]] = {
    RunPhase.IDLE: [RunPhase.PLANNING, RunPhase.EXECUTING],
    RunPhase.PLANNING: [
        RunPhase.EXECUTING,
        RunPhase.WAITING_FOR_USER,
        RunPhase.FAILED,
        RunPhase.CANCELLED,
    ],
    RunPhase.EXECUTING: [
        RunPhase.VERIFYING,
        RunPhase.WAITING_FOR_USER,
        RunPhase.COMPLETED,
        RunPhase.FAILED,
        RunPhase.CANCELLED,
    ],
    RunPhase.WAITING_FOR_USER: [
        RunPhase.EXECUTING,
        RunPhase.CANCELLED,
        RunPhase.FAILED,
    ],
    RunPhase.VERIFYING: [
        RunPhase.COMPLETED,
        RunPhase.EXECUTING,
        RunPhase.FAILED,
    ],
    RunPhase.COMPLETED: [],
    RunPhase.FAILED: [RunPhase.EXECUTING],  # retry
    RunPhase.CANCELLED: [],
}


def is_valid_transition(from_phase: RunPhase, to_phase: RunPhase) -> bool:
    """Check if a phase transition is valid."""
    return to_phase in PHASE_TRANSITIONS.get(from_phase, [])


def is_terminal_phase(phase: RunPhase) -> bool:
    """Check if a phase is terminal (no further transitions)."""
    return phase in (RunPhase.COMPLETED, RunPhase.CANCELLED)


# ============================================================
# Step Types
# ============================================================

class StepType(str, Enum):
    """Types of execution steps."""

    ANALYZE = "analyze"
    RETRIEVE = "retrieve"
    READ = "read"
    TOOL_CALL = "tool_call"
    SYNTHESIZE = "synthesize"
    VERIFY = "verify"
    CONFIRM = "confirm"


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


# ============================================================
# Core Models
# ============================================================

class Run(BaseModel):
    """Top-level execution unit for agent runs.

    Each user message initiates a Run that tracks the full lifecycle
    from planning through verification.
    """

    run_id: str = Field(..., description="Unique run identifier")
    session_id: str = Field(..., description="Parent session ID")
    message_id: str = Field(..., description="Bound assistant message ID")
    scope: str = Field(
        default="general",
        description="Scope: general | single_paper | full_kb",
    )
    objective: str = Field(default="", description="User's objective/query")
    mode: Literal["auto", "rag", "agent"] = Field(
        default="auto",
        description="Execution mode",
    )
    status: RunPhase = Field(
        default=RunPhase.IDLE,
        description="Current run phase",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    ended_at: Optional[datetime] = Field(default=None)
    current_step_id: Optional[str] = Field(default=None)
    confirmation_required: bool = Field(default=False)
    recoverable: bool = Field(default=True)
    final_summary: Optional["FinalSummary"] = Field(default=None)

    model_config = {"use_enum_values": True}


class RunStep(BaseModel):
    """Ordered execution step within a run."""

    step_id: str = Field(..., description="Unique step identifier")
    run_id: str = Field(..., description="Parent run ID")
    type: StepType = Field(..., description="Step type")
    title: str = Field(default="", description="Human-readable step title")
    description: str = Field(default="", description="Step description")
    status: StepStatus = Field(default=StepStatus.PENDING)
    order: int = Field(default=0, description="Execution order")
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    verification_status: Optional[Literal["pass", "fail", "skip"]] = Field(
        default=None,
    )

    model_config = {"use_enum_values": True}


class ToolEvent(BaseModel):
    """Tool call or result event within a step."""

    event_id: str = Field(..., description="Unique event identifier")
    run_id: str = Field(..., description="Parent run ID")
    step_id: str = Field(..., description="Parent step ID")
    tool_name: str = Field(..., description="Tool identifier")
    event_type: Literal["call", "result", "error"] = Field(
        ..., description="Event type",
    )
    label: str = Field(default="", description="Human-readable label")
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    status: Literal["running", "success", "failed"] = Field(default="running")


class ConfirmationRequest(BaseModel):
    """Confirmation request for dangerous operations.

    First-class runtime state, not an ad-hoc dialog.
    """

    confirmation_id: str = Field(..., description="Unique confirmation ID")
    run_id: str = Field(..., description="Parent run ID")
    step_id: str = Field(..., description="Parent step ID")
    reason: str = Field(..., description="Why confirmation is needed")
    risk_level: Literal["low", "medium", "high"] = Field(default="medium")
    proposed_action: str = Field(
        default="",
        description="What will be done if approved",
    )
    tool_name: str = Field(default="")
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = Field(default=None)


class RunArtifact(BaseModel):
    """Generated output artifact from a run."""

    artifact_id: str = Field(..., description="Unique artifact ID")
    run_id: str = Field(..., description="Parent run ID")
    type: Literal[
        "citation", "note", "summary", "file", "extracted_result", "download",
    ] = Field(..., description="Artifact type")
    title: str = Field(default="")
    content: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunEvidence(BaseModel):
    """Citation evidence binding for answer verification."""

    source_id: str = Field(..., description="Source paper or document ID")
    title: str = Field(default="")
    page_num: Optional[int] = Field(default=None)
    section_path: Optional[str] = Field(default=None)
    anchor_text: Optional[str] = Field(default=None)
    text_preview: str = Field(default="")
    relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    consistency: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class FinalSummary(BaseModel):
    """Structured final output of an agent run.

    Not just text - carries evidence, artifacts, and confidence.
    """

    answer: str = Field(default="", description="Main answer text")
    citations: List[RunEvidence] = Field(default_factory=list)
    artifacts: List[RunArtifact] = Field(default_factory=list)
    answer_evidence_consistency: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="How well the answer is supported by evidence",
    )
    low_confidence_reasons: List[str] = Field(
        default_factory=list,
        description="Reasons for low confidence, if any",
    )
    step_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Summary of each step executed",
    )
    tokens_used: int = Field(default=0)
    cost: float = Field(default=0.0)


# ============================================================
# SSE Event Extensions for Run Protocol
# ============================================================

class RunStartEventData(BaseModel):
    """Emitted when a run begins."""

    run_id: str
    session_id: str
    message_id: str
    scope: str
    mode: str
    objective: str


class RunPhaseChangeEventData(BaseModel):
    """Emitted when run phase changes."""

    run_id: str
    phase: str
    previous_phase: str
    label: str


class StepStartEventData(BaseModel):
    """Emitted when a step begins."""

    run_id: str
    step_id: str
    step_type: str
    title: str
    order: int


class StepCompleteEventData(BaseModel):
    """Emitted when a step completes."""

    run_id: str
    step_id: str
    status: str
    verification_status: Optional[str] = None


class RunCompleteEventData(BaseModel):
    """Emitted when a run completes."""

    run_id: str
    status: str
    final_summary: Optional[Dict[str, Any]] = None
    tokens_used: int = 0
    cost: float = 0.0


class RecoveryActionData(BaseModel):
    """Available recovery actions for the frontend."""

    run_id: str
    available_actions: List[Literal[
        "retry", "resume", "cancel", "confirm", "reject",
    ]]
    context: Dict[str, Any] = Field(default_factory=dict)
