"""Context helpers for request/run observability fields."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
message_id_var: ContextVar[str | None] = ContextVar("message_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)
paper_id_var: ContextVar[str | None] = ContextVar("paper_id", default=None)
kb_id_var: ContextVar[str | None] = ContextVar("kb_id", default=None)
query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
route_var: ContextVar[str | None] = ContextVar("route", default=None)

_CONTEXT_VARS = {
    "request_id": request_id_var,
    "run_id": run_id_var,
    "session_id": session_id_var,
    "message_id": message_id_var,
    "job_id": job_id_var,
    "paper_id": paper_id_var,
    "kb_id": kb_id_var,
    "query_id": query_id_var,
    "user_id": user_id_var,
    "route": route_var,
}


def set_request_context(
    request_id: str,
    route: str | None = None,
    user_id: str | None = None,
) -> None:
    request_id_var.set(request_id)
    route_var.set(route)
    user_id_var.set(user_id)


def set_run_context(
    run_id: str,
    session_id: str | None = None,
    message_id: str | None = None,
    job_id: str | None = None,
    paper_id: str | None = None,
    kb_id: str | None = None,
    query_id: str | None = None,
) -> None:
    run_id_var.set(run_id)
    session_id_var.set(session_id)
    message_id_var.set(message_id)
    job_id_var.set(job_id)
    paper_id_var.set(paper_id)
    kb_id_var.set(kb_id)
    query_id_var.set(query_id)


def bind_optional_context(**fields: Any) -> None:
    for key, value in fields.items():
        if key in _CONTEXT_VARS:
            _CONTEXT_VARS[key].set(value)


def clear_context() -> None:
    for context_var in _CONTEXT_VARS.values():
        context_var.set(None)


def current_context_dict() -> Dict[str, str]:
    return {
        key: value
        for key, context_var in _CONTEXT_VARS.items()
        if (value := context_var.get()) is not None
    }
