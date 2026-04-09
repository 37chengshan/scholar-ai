"""Request logging middleware for FastAPI.

Provides structured logging for incoming requests and outgoing responses.
Includes request ID for tracing and skips health check endpoints.

Usage:
    from app.middleware.logging import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.utils.logger import logger


# Endpoints to skip logging (reduce noise)
SKIP_LOG_PATHS = [
    "/health",
    "/health/",
]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    Logs:
    - Request start: method, path, client IP, request_id
    - Request complete: method, path, status, duration, request_id

    Features:
    - Request ID from X-Request-ID header or generated UUID
    - Structured logging with structlog
    - Skip logging for health check endpoints
    - Duration in milliseconds

    Example log output:
        request_started: GET /api/v1/papers abc123
        request_completed: GET /api/v1/papers 200 45ms abc123
    """

    def __init__(self, app: ASGIApp):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log before/after.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/route handler

        Returns:
            Response from the handler
        """
        # Skip logging for health endpoints
        if request.url.path in SKIP_LOG_PATHS:
            return await call_next(request)

        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Get client IP (handle proxy headers)
        client_ip = request.headers.get("X-Forwarded-For", "")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            client_ip=client_ip,
        )

        # Track timing
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception before re-raising
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                error=str(exc),
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request completion
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


__all__ = ["RequestLoggingMiddleware"]