"""日志工具

Per Review Fix #8: 全链路 trace 追踪。
"""

import logging
import os
from typing import Any, Dict

import structlog

def _resolve_log_level(raw_level: str | None) -> int:
    """Resolve LOG_LEVEL env value into a valid logging level int."""
    value = (raw_level or "INFO").strip()
    if value.isdigit():
        return int(value)

    normalized = value.upper()
    if normalized.startswith("LEVEL "):
        normalized = normalized.split(" ", 1)[1].strip()

    return logging.getLevelNamesMapping().get(normalized, logging.INFO)



# 配置 structlog (compatible with structlog 25.x)
# merge_contextvars processor automatically adds all bound contextvars to event dict
# Including: trace_id, paper_id, task_id (when bound via bind_contextvars)
structlog.configure(
    processors=[
        # 自动合并 contextvars 到日志事件
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if os.getenv("LOG_FORMAT") == "console"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        _resolve_log_level(os.getenv("LOG_LEVEL"))
    ),
)

logger = structlog.get_logger()


def get_logger(name: str | None = None, **bind_fields: Any):
    """Backward-compatible logger factory.

    Some modules still import ``get_logger`` from this utility.
    Keep the API stable while migrating to direct ``structlog.get_logger`` usage.
    """
    target = structlog.get_logger(name) if name else structlog.get_logger()
    return target.bind(**bind_fields) if bind_fields else target


OBSERVABILITY_KEYS = (
    "request_id",
    "run_id",
    "session_id",
    "message_id",
    "job_id",
    "paper_id",
    "kb_id",
    "query_id",
    "user_id",
    "route",
)


def bind_request_context(
    request_id: str,
    route: str | None = None,
    user_id: str | None = None,
    **extra: Any,
) -> None:
    """Bind request-scoped observability fields to structlog contextvars."""
    payload: Dict[str, Any] = {"request_id": request_id}
    if route:
        payload["route"] = route
    if user_id:
        payload["user_id"] = user_id
    payload.update({k: v for k, v in extra.items() if v is not None})
    structlog.contextvars.bind_contextvars(**payload)


def bind_run_context(
    run_id: str,
    session_id: str | None = None,
    message_id: str | None = None,
    job_id: str | None = None,
    paper_id: str | None = None,
    kb_id: str | None = None,
    query_id: str | None = None,
    **extra: Any,
) -> None:
    """Bind run-scoped observability fields to structlog contextvars."""
    payload: Dict[str, Any] = {"run_id": run_id}
    optional_fields = {
        "session_id": session_id,
        "message_id": message_id,
        "job_id": job_id,
        "paper_id": paper_id,
        "kb_id": kb_id,
        "query_id": query_id,
    }
    payload.update({k: v for k, v in optional_fields.items() if v is not None})
    payload.update({k: v for k, v in extra.items() if v is not None})
    structlog.contextvars.bind_contextvars(**payload)


def clear_observability_context() -> None:
    """Clear all structlog contextvars bound during request/run lifecycle."""
    structlog.contextvars.clear_contextvars()