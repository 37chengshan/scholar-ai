"""Request-scoped observability middleware.

Merges request logging (SKIP_LOG_PATHS, structured logs) with observability
context binding (trace_id, request_id, route).

Slow requests (>2000ms) trigger a warning log.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.observability.context import clear_context, set_request_context
from app.utils.logger import bind_request_context, clear_observability_context, logger

# Endpoints to skip logging (reduce noise)
SKIP_LOG_PATHS = [
    "/health",
    "/health/",
]

# SLO threshold: requests slower than this trigger a warning
SLOW_REQUEST_THRESHOLD_MS = 2000


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Bind request_id/route context, log requests, and warn on slow responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        route = request.url.path
        user_id = getattr(request.state, "user_id", None)
        start = time.perf_counter()
        should_defer_cleanup = False

        request.state.request_id = request_id
        request.state.trace_id = request_id
        request.state.route = route

        set_request_context(request_id=request_id, route=route, user_id=user_id)
        bind_request_context(request_id=request_id, route=route, user_id=user_id)

        # Skip logging for health endpoints
        should_log = route not in SKIP_LOG_PATHS

        if should_log:
            logger.info(
                "request_started",
                method=request.method,
                route=route,
                event_type="request_started",
            )

        try:
            response = await call_next(request)
            user_id = getattr(request.state, "user_id", user_id)
            bind_request_context(request_id=request_id, route=route, user_id=user_id)
            duration_ms = (time.perf_counter() - start) * 1000

            if should_log:
                logger.info(
                    "request_completed",
                    method=request.method,
                    route=route,
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    event_type="request_completed",
                )

            # Slow request warning
            if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
                logger.warning(
                    "slow_request",
                    method=request.method,
                    route=route,
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=SLOW_REQUEST_THRESHOLD_MS,
                    event_type="slow_request",
                )

            response.headers["X-Request-ID"] = request_id

            # Keep context until stream completes; otherwise SSE chunks lose request linkage.
            is_streaming = bool(getattr(response, "body_iterator", None)) and response.headers.get(
                "content-type", ""
            ).startswith("text/event-stream")
            if is_streaming:
                original_iterator = response.body_iterator
                should_defer_cleanup = True

                async def wrapped_iterator():
                    try:
                        async for chunk in original_iterator:
                            yield chunk
                    finally:
                        clear_context()
                        clear_observability_context()

                response.body_iterator = wrapped_iterator()
                return response

            return response
        except Exception as exc:
            user_id = getattr(request.state, "user_id", user_id)
            bind_request_context(request_id=request_id, route=route, user_id=user_id)
            duration_ms = (time.perf_counter() - start) * 1000
            if should_log:
                logger.error(
                    "request_failed",
                    method=request.method,
                    route=route,
                    duration_ms=round(duration_ms, 2),
                    error=str(exc),
                    event_type="request_failed",
                )
            raise
        finally:
            if not should_defer_cleanup:
                clear_context()
                clear_observability_context()


__all__ = ["ObservabilityMiddleware", "SKIP_LOG_PATHS", "SLOW_REQUEST_THRESHOLD_MS"]
