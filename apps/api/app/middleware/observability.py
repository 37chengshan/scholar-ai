"""Request-scoped observability middleware."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.observability.context import clear_context, set_request_context
from app.utils.logger import bind_request_context, clear_observability_context, logger


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Bind request_id and route context for each HTTP request."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        route = request.url.path
        user_id = getattr(request.state, "user_id", None)
        start = time.perf_counter()
        should_defer_cleanup = False

        set_request_context(request_id=request_id, route=route, user_id=user_id)
        bind_request_context(request_id=request_id, route=route, user_id=user_id)

        logger.info(
            "request_started",
            method=request.method,
            route=route,
            event_type="request_started",
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request_completed",
                method=request.method,
                route=route,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                event_type="request_completed",
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
            duration_ms = (time.perf_counter() - start) * 1000
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


__all__ = ["ObservabilityMiddleware"]
