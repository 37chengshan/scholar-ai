"""Decorators for phase/tool/pipeline observability."""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from app.core.observability.events import build_error_event, build_phase_event, build_tool_event
from app.utils.logger import logger


F = TypeVar("F", bound=Callable[..., Any])


def observe_phase(phase_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.perf_counter()
            logger.info("phase_started", **build_phase_event(phase=phase_name, status="started"))
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.info(
                    "phase_completed",
                    **build_phase_event(
                        phase=phase_name,
                        status="completed",
                        duration_ms=duration_ms,
                    ),
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.error(
                    "phase_failed",
                    **build_error_event(
                        event_type="phase_failed",
                        message=str(exc),
                        phase=phase_name,
                        duration_ms=duration_ms,
                    ),
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def observe_tool(tool_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.perf_counter()
            logger.info("tool_call_started", **build_tool_event(tool_name=tool_name, status="started"))
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.info(
                    "tool_call_completed",
                    **build_tool_event(
                        tool_name=tool_name,
                        status="completed",
                        duration_ms=duration_ms,
                    ),
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.error(
                    "tool_call_failed",
                    **build_error_event(
                        event_type="tool_call_failed",
                        message=str(exc),
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                    ),
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def observe_pipeline(pipeline_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.perf_counter()
            logger.info("run_started", pipeline=pipeline_name)
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.info(
                    "run_completed",
                    pipeline=pipeline_name,
                    duration_ms=round(duration_ms, 2),
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.error(
                    "run_failed",
                    pipeline=pipeline_name,
                    duration_ms=round(duration_ms, 2),
                    error=str(exc),
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
