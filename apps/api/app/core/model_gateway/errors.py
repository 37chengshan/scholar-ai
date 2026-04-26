"""Model Gateway error taxonomy for v2.3 API-first stack."""

from typing import Any, Dict, Optional


class ProviderError(Exception):
    """Base error for all provider failures."""

    def __init__(
        self,
        message: str,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model_name = model_name
        self.context = context or {}


class ProviderTimeout(ProviderError):
    """Provider request timed out."""


class ProviderRateLimited(ProviderError):
    """Provider returned rate-limit response."""


class ProviderDimensionMismatch(ProviderError):
    """Embedding dimension does not match expected schema."""


class ProviderAuthError(ProviderError):
    """Provider authentication failed."""


class ProviderBadResponse(ProviderError):
    """Provider response is invalid or incomplete."""


class ProviderUnavailable(ProviderError):
    """Provider endpoint unavailable or network failure."""
