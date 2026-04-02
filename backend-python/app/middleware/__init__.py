"""Middleware for request validation and processing."""

from app.middleware.file_validation import validate_pdf_upload

__all__ = ["validate_pdf_upload"]