"""Middleware for request validation and processing.

Available middleware:
- validate_pdf_upload: PDF file validation decorator
- get_cors_config: CORS configuration function
- RequestLoggingMiddleware: Structured request logging
- setup_error_handlers: RFC 7807 error handler registration
"""

from app.middleware.file_validation import validate_pdf_upload
from app.middleware.cors import get_cors_config
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.error_handler import setup_error_handlers

__all__ = [
    "validate_pdf_upload",
    "get_cors_config",
    "RequestLoggingMiddleware",
    "setup_error_handlers",
]