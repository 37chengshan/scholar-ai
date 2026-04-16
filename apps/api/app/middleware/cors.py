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

# Default development origins when no specific hosts are configured.
# Browser spec: credentials=True is incompatible with wildcard origin ["*"].
# These cover the Vite dev server, common CRA port, and Node gateway.
_DEV_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4000",
    "http://127.0.0.1:8000",
]


def get_cors_config() -> dict:
    """Get CORS configuration for FastAPI.

    Returns a dict suitable for passing to CORSMiddleware.

    Configuration:
        allow_origins: ALLOWED_HOSTS from settings.
                       When the setting contains ["*"] (wildcard), it is
                       automatically replaced with a safe set of localhost
                       origins so that allow_credentials=True remains valid.
                       In production, ALLOWED_HOSTS must list explicit origins.
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
        - NOT ["*"] with credentials=True (browser security violation per
          the Fetch spec – browsers will reject such responses outright).
    """
    # Get origins from settings.
    # In development this is typically ["*"]; production must use explicit URLs.
    configured: List[str] = list(settings.ALLOWED_HOSTS)

    # -----------------------------------------------------------------------
    # Critical fix: the Fetch/CORS spec forbids pairing
    #   Access-Control-Allow-Origin: *
    # with
    #   Access-Control-Allow-Credentials: true
    # Browsers reject such responses with a CORS error.
    # When the administrator has left the default wildcard, fall back to an
    # explicit list of localhost origins that cover all common dev setups.
    # -----------------------------------------------------------------------
    if "*" in configured or configured == ["*"]:
        allow_origins: List[str] = _DEV_ORIGINS
    else:
        allow_origins = configured

    return {
        # Origins permitted to make credentialed cross-origin requests.
        "allow_origins": allow_origins,
        # Allow cookies / Authorization headers to be sent with requests.
        # REQUIRED for httpOnly cookie-based authentication.
        # WARNING: Must never be combined with allow_origins=["*"].
        "allow_credentials": True,
        # HTTP methods allowed by the API.
        "allow_methods": [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        # Request headers the client is allowed to send.
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "Accept",
            "Origin",
            "Cookie",
        ],
        # Response headers the client-side JavaScript may access.
        "expose_headers": ["X-Request-ID"],
        # Cache preflight (OPTIONS) responses for 10 minutes to reduce
        # round-trips on repeat API calls.
        "max_age": 600,
    }


__all__ = ["get_cors_config"]
