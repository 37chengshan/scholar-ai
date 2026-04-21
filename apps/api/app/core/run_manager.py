"""Run Manager — Agent run lifecycle state machine.

Manages Run/Step/ToolEvent lifecycle with deterministic phase transitions.
This is the system-level coordinator for agent-native execution.

Per 战役 B WP6: Planner / Executor / Verifier run layering.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.run import (
    ConfirmationRequest,
    FinalSummary,
    Run,
    RunArtifact,
    RunEvidence,
    RunPhase,
    RunStep,
    StepStatus,
    StepType,
    ToolEvent,
    is_terminal_phase,
    is_valid_transition,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _new_id() -> str:
    return str(uuid.uuid4())


class RunManager:
    """Manages agent run lifecycle with deterministic state machine.

    Thread-safe run state management. One RunManager per run execution.
    """

    def __init__(
        self,
        session_id: str,
        message_id: str,
        objective: str,
        scope: str = "general",
        mode: str = "auto",
    ) -> None:
        self._run = Run(
            run_id=_new_id(),
            session_id=session_id,
            message_id=message_id,
            scope=scope,
            objective=objective,
            mode=mode,
            status=RunPhase.IDLE,
        )
        self._steps: List[RunStep] = []
        self._tool_events: List[ToolEvent] = []
        self._artifacts: List[RunArtifact] = []
        self._evidence: List[RunEvidence] = []
        self._confirmation: Optional[ConfirmationRequest] = None
        self._step_counter = 0

    # ── Properties ────────────────────────────────────────────

    @property
    def run(self) -> Run:
        return self._run

    @property
    def run_id(self) -> str:
        return self._run.run_id

    @property
    def phase(self) -> RunPhase:
        return RunPhase(self._run.status)

    @property
    def steps(self) -> List[RunStep]:
        return list(self._steps)

    @property
    def tool_events(self) -> List[ToolEvent]:
        return list(self._tool_events)

    @property
    def artifacts(self) -> List[RunArtifact]:
        return list(self._artifacts)

    @property
    def evidence(self) -> List[RunEvidence]:
        return list(self._evidence)

    @property
    def confirmation(self) -> Optional[ConfirmationRequest]:
        return self._confirmation

    @property
    def current_step(self) -> Optional[RunStep]:
        if not self._run.current_step_id:
            return None
        return next(
            (s for s in self._steps if s.step_id == self._run.current_step_id),
            None,
        )

    # ── Phase Transitions ─────────────────────────────────────

    def transition_to(self, new_phase: RunPhase) -> bool:
        """Attempt a phase transition. Returns True if successful."""
        current = RunPhase(self._run.status)
        if is_terminal_phase(current) and new_phase != RunPhase.EXECUTING:
            logger.warning(
                "Cannot transition from terminal phase %s to %s",
                current.value,
                new_phase.value,
            )
            return False

        if not is_valid_transition(current, new_phase):
            logger.warning(
                "Invalid transition: %s -> %s", current.value, new_phase.value,
            )
            return False

        previous = current.value
        self._run = self._run.model_copy(update={"status": new_phase.value})
        logger.info(
            "Run %s: %s -> %s", self.run_id, previous, new_phase.value,
        )
        return True

    def start(self) -> None:
        """Start the run: idle -> planning/executing."""
        self.transition_to(RunPhase.PLANNING)

    def begin_execution(self) -> None:
        """Move to executing phase."""
        self.transition_to(RunPhase.EXECUTING)

    def request_confirmation(
        self,
        step_id: str,
        reason: str,
        tool_name: str,
        risk_level: str = "medium",
        proposed_action: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> ConfirmationRequest:
        """Request user confirmation — transitions to waiting_for_user."""
        confirmation = ConfirmationRequest(
            confirmation_id=_new_id(),
            run_id=self.run_id,
            step_id=step_id,
            reason=reason,
            risk_level=risk_level,
            proposed_action=proposed_action,
            tool_name=tool_name,
            payload=payload or {},
        )
        self._confirmation = confirmation
        self._run = self._run.model_copy(update={"confirmation_required": True})
        self.transition_to(RunPhase.WAITING_FOR_USER)
        return confirmation

    def resolve_confirmation(self, approved: bool) -> None:
        """Resolve pending confirmation."""
        self._confirmation = None
        self._run = self._run.model_copy(
            update={"confirmation_required": False},
        )
        if approved:
            self.transition_to(RunPhase.EXECUTING)
        else:
            self.transition_to(RunPhase.CANCELLED)

    def begin_verification(self) -> None:
        """Move to verification phase."""
        self.transition_to(RunPhase.VERIFYING)

    def complete(self, summary: Optional[FinalSummary] = None) -> None:
        """Mark run as completed."""
        self._run = self._run.model_copy(
            update={
                "ended_at": datetime.now(timezone.utc),
                "final_summary": summary,
            },
        )
        self.transition_to(RunPhase.COMPLETED)

    def fail(self, error: Optional[str] = None) -> None:
        """Mark run as failed."""
        self._run = self._run.model_copy(
            update={"ended_at": datetime.now(timezone.utc)},
        )
        self.transition_to(RunPhase.FAILED)

    def cancel(self) -> None:
        """Cancel the run."""
        self._run = self._run.model_copy(
            update={"ended_at": datetime.now(timezone.utc)},
        )
        self.transition_to(RunPhase.CANCELLED)

    def retry(self) -> bool:
        """Retry a failed run."""
        if RunPhase(self._run.status) != RunPhase.FAILED:
            return False
        self._run = self._run.model_copy(
            update={
                "ended_at": None,
                "recoverable": True,
            },
        )
        return self.transition_to(RunPhase.EXECUTING)

    # ── Step Management ───────────────────────────────────────

    def add_step(
        self,
        step_type: StepType,
        title: str = "",
        description: str = "",
    ) -> RunStep:
        """Add a new step to the run."""
        self._step_counter += 1
        step = RunStep(
            step_id=_new_id(),
            run_id=self.run_id,
            type=step_type,
            title=title,
            description=description,
            status=StepStatus.PENDING,
            order=self._step_counter,
        )
        self._steps.append(step)
        return step

    def start_step(self, step_id: str) -> Optional[RunStep]:
        """Mark a step as running."""
        step = self._find_step(step_id)
        if not step:
            return None
        updated = step.model_copy(
            update={
                "status": StepStatus.RUNNING.value,
                "started_at": datetime.now(timezone.utc),
            },
        )
        self._replace_step(step_id, updated)
        self._run = self._run.model_copy(update={"current_step_id": step_id})
        return updated

    def complete_step(
        self,
        step_id: str,
        verification_status: Optional[str] = None,
    ) -> Optional[RunStep]:
        """Mark a step as completed."""
        step = self._find_step(step_id)
        if not step:
            return None
        updated = step.model_copy(
            update={
                "status": StepStatus.COMPLETED.value,
                "ended_at": datetime.now(timezone.utc),
                "verification_status": verification_status,
            },
        )
        self._replace_step(step_id, updated)
        return updated

    def fail_step(self, step_id: str) -> Optional[RunStep]:
        """Mark a step as failed."""
        step = self._find_step(step_id)
        if not step:
            return None
        updated = step.model_copy(
            update={
                "status": StepStatus.FAILED.value,
                "ended_at": datetime.now(timezone.utc),
            },
        )
        self._replace_step(step_id, updated)
        return updated

    # ── Tool Events ───────────────────────────────────────────

    def record_tool_call(
        self,
        step_id: str,
        tool_name: str,
        label: str = "",
        args: Optional[Dict[str, Any]] = None,
    ) -> ToolEvent:
        """Record a tool call event."""
        event = ToolEvent(
            event_id=_new_id(),
            run_id=self.run_id,
            step_id=step_id,
            tool_name=tool_name,
            event_type="call",
            label=label or tool_name,
            args=args or {},
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self._tool_events.append(event)
        return event

    def record_tool_result(
        self,
        event_id: str,
        result: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        success: bool = True,
    ) -> Optional[ToolEvent]:
        """Record tool result for an existing call event."""
        idx = next(
            (i for i, e in enumerate(self._tool_events) if e.event_id == event_id),
            None,
        )
        if idx is None:
            return None
        existing = self._tool_events[idx]
        updated = existing.model_copy(
            update={
                "event_type": "result" if success else "error",
                "result": result,
                "summary": summary,
                "ended_at": datetime.now(timezone.utc),
                "status": "success" if success else "failed",
            },
        )
        self._tool_events[idx] = updated
        return updated

    # ── Artifacts & Evidence ──────────────────────────────────

    def add_artifact(
        self,
        artifact_type: str,
        title: str = "",
        content: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RunArtifact:
        """Add an artifact to the run."""
        artifact = RunArtifact(
            artifact_id=_new_id(),
            run_id=self.run_id,
            type=artifact_type,
            title=title,
            content=content,
            url=url,
            metadata=metadata or {},
        )
        self._artifacts.append(artifact)
        return artifact

    def add_evidence(
        self,
        source_id: str,
        title: str = "",
        text_preview: str = "",
        page_num: Optional[int] = None,
        section_path: Optional[str] = None,
        relevance: Optional[float] = None,
        consistency: Optional[float] = None,
    ) -> RunEvidence:
        """Add evidence to the run."""
        evidence = RunEvidence(
            source_id=source_id,
            title=title,
            text_preview=text_preview,
            page_num=page_num,
            section_path=section_path,
            relevance=relevance,
            consistency=consistency,
        )
        self._evidence.append(evidence)
        return evidence

    # ── Snapshot ──────────────────────────────────────────────

    def build_final_summary(
        self,
        answer: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        consistency: Optional[float] = None,
        low_confidence_reasons: Optional[List[str]] = None,
    ) -> FinalSummary:
        """Build a structured final summary."""
        step_summary = [
            {
                "step_id": s.step_id,
                "type": s.type,
                "title": s.title,
                "status": s.status,
                "order": s.order,
            }
            for s in self._steps
        ]
        return FinalSummary(
            answer=answer,
            citations=list(self._evidence),
            artifacts=list(self._artifacts),
            answer_evidence_consistency=consistency,
            low_confidence_reasons=low_confidence_reasons or [],
            step_summary=step_summary,
            tokens_used=tokens_used,
            cost=cost,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize current run state for SSE emission."""
        return {
            "run": self._run.model_dump(mode="json"),
            "steps": [s.model_dump(mode="json") for s in self._steps],
            "tool_events": [e.model_dump(mode="json") for e in self._tool_events],
            "artifacts": [a.model_dump(mode="json") for a in self._artifacts],
            "evidence": [e.model_dump() for e in self._evidence],
        }

    # ── Private Helpers ───────────────────────────────────────

    def _find_step(self, step_id: str) -> Optional[RunStep]:
        return next((s for s in self._steps if s.step_id == step_id), None)

    def _replace_step(self, step_id: str, updated: RunStep) -> None:
        self._steps = [
            updated if s.step_id == step_id else s for s in self._steps
        ]
