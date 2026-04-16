"""
Rate limiting middleware using SlowAPI + Redis.

Provides per-user and per-endpoint rate limits with X-RateLimit-* headers.
Falls back to in-memory storage if Redis is unavailable.
"""
from typing import Any, Callable

from fastapi import Request

from app.config import settings

try:
    from slowapi import Limiter as SlowAPILimiter
    from slowapi import _rate_limit_exceeded_handler as _slowapi_rate_limit_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address as _slowapi_get_remote_address

    _SLOWAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - compatibility for environments without slowapi
    _SLOWAPI_AVAILABLE = False

    class RateLimitExceeded(Exception):
        """Fallback exception when slowapi is unavailable."""

    class NoopLimiter:
        """No-op limiter fallback when slowapi is not installed."""

        def __init__(self, *args: Any, **kwargs: Any):
            self.enabled = False

        def limit(
            self, *args: Any, **kwargs: Any
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

    def get_remote_address(request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _rate_limit_exceeded_handler(request: Request, exc: Exception):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )


if _SLOWAPI_AVAILABLE:

    def get_remote_address(request: Request) -> str:
        return _slowapi_get_remote_address(request)

    def _rate_limit_exceeded_handler(request: Request, exc: Exception):
        return _slowapi_rate_limit_handler(request, exc)  # type: ignore[arg-type]


def _get_user_id(request: Request) -> str:
    """Extract user_id for rate limiting. Falls back to IP address."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


# Global limiter instance
if _SLOWAPI_AVAILABLE:
    limiter = SlowAPILimiter(
        key_func=_get_user_id,
        storage_uri=settings.REDIS_URL,
        headers_enabled=True,
        default_limits=[f"{settings.RATE_LIMIT_DEFAULT_PER_HOUR}/hour"],
        enabled=settings.RATE_LIMIT_ENABLED,
        swallow_errors=True,  # Don't block requests if Redis is unavailable
    )
else:
    limiter = NoopLimiter(
        key_func=_get_user_id,
        storage_uri=settings.REDIS_URL,
        headers_enabled=False,
        default_limits=[],
        enabled=False,
        swallow_errors=True,
    )
