"""日志工具

Per Review Fix #8: 全链路 trace 追踪。
"""

import logging
import os
from typing import Any, Dict

import structlog


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
        logging.getLevelName(os.getenv("LOG_LEVEL", "INFO"))
    ),
)

logger = structlog.get_logger()


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