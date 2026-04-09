"""CORS middleware configuration for FastAPI.

Provides CORS settings matching the Node.js backend configuration.
Per D-03: Same origin allowlist, credentials enabled for httpOnly cookies.

Usage:
    from app.middleware.cors import get_cors_config
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(CORSMiddleware, **get_cors_config())

Security Notes:
    - DON'T use ["*"] in production with credentials=True
    - Specify exact origins in production environment
    - Credentials=True is required for cookie-based authentication
"""

from typing import List

from app.config import settings


def get_cors_config() -> dict:
    """Get CORS configuration for FastAPI.

    Returns a dict suitable for passing to CORSMiddleware.

    Configuration:
        allow_origins: ALLOWED_HOSTS from settings, or ["*"] for development
        allow_credentials: True (required for httpOnly cookies)
        allow_methods: All standard HTTP methods
        allow_headers: Content-Type, Authorization, X-Request-ID, Accept, Origin
        expose_headers: X-Request-ID (for client-side access)
        max_age: 600 seconds (preflight cache duration)

    Returns:
        dict: CORS configuration parameters

    Example:
        >>> config = get_cors_config()
        >>> app.add_middleware(CORSMiddleware, **config)

    Security Warning:
        In production, ALLOWED_HOSTS should be a list of specific origins:
        - ["https://app.example.com", "https://admin.example.com"]
        - NOT ["*"] with credentials=True (browser security violation)
    """
    # Get origins from settings
    # In development, this may be ["*"]
    # In production, should be specific frontend URLs
    allow_origins: List[str] = settings.ALLOWED_HOSTS

    # CORS configuration matching Node.js backend
    return {
        # Origins allowed to make requests
        # IMPORTANT: In production, use specific origins, not ["*"]
        "allow_origins": allow_origins,

        # Allow cookies to be sent with requests
        # REQUIRED for httpOnly cookie-based authentication
        # WARNING: Cannot use ["*"] origins with credentials=True
        "allow_credentials": True,

        # HTTP methods allowed
        # Include all methods used by the API
        "allow_methods": [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],

        # Headers allowed in requests
        # Include headers used by authentication and logging
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "Accept",
            "Origin",
            "Cookie",
        ],

        # Headers exposed to client-side JavaScript
        # X-Request-ID for request tracing
        "expose_headers": ["X-Request-ID"],

        # Preflight request cache duration in seconds
        # Reduce preflight requests for repeated API calls
        "max_age": 600,
    }


__all__ = ["get_cors_config"]