"""Structured event builders for observability logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_event(
    event_type: str,
    status: str = "ok",
    phase: str | None = None,
    duration_ms: float | None = None,
    **payload: Any,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "event_type": event_type,
        "status": status,
        "timestamp": _now_iso(),
    }
    if phase is not None:
        event["phase"] = phase
    if duration_ms is not None:
        event["duration_ms"] = round(duration_ms, 2)
    event.update(payload)
    return event


def build_phase_event(
    phase: str,
    status: str,
    duration_ms: float | None = None,
    **payload: Any,
) -> Dict[str, Any]:
    return build_event(
        event_type=f"phase_{status}",
        status=status,
        phase=phase,
        duration_ms=duration_ms,
        **payload,
    )


def build_tool_event(
    tool_name: str,
    status: str,
    duration_ms: float | None = None,
    **payload: Any,
) -> Dict[str, Any]:
    return build_event(
        event_type=f"tool_call_{status}",
        status=status,
        tool_name=tool_name,
        duration_ms=duration_ms,
        **payload,
    )


def build_error_event(
    event_type: str,
    message: str,
    code: str | None = None,
    **payload: Any,
) -> Dict[str, Any]:
    return build_event(
        event_type=event_type,
        status="error",
        error_message=message,
        error_code=code,
        **payload,
    )


def build_metric_payload(**metrics: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in metrics.items()
        if value is not None
    }
