"""RFC 7807 Problem Details for HTTP APIs.

Provides structured error responses matching Node.js implementation.
https://tools.ietf.org/html/rfc7807

Usage:
    from app.utils.problem_detail import ProblemDetail, ErrorTypes, create_error

    raise HTTPException(
        status_code=404,
        detail=create_error(
            error_type=ErrorTypes.NOT_FOUND,
            title="Paper Not Found",
            detail="The requested paper does not exist",
            instance="/api/papers/123"
        )
    )
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class ProblemDetail:
    """RFC 7807 Problem Detail object.

    Matches Node.js ProblemDetail interface from auth.ts.
    """
    type: str           # URI reference to error documentation
    title: str          # Human-readable summary
    status: int         # HTTP status code
    detail: Optional[str] = None      # Detailed explanation
    instance: Optional[str] = None    # Request path
    request_id: Optional[str] = None  # For log correlation
    timestamp: Optional[str] = None   # ISO 8601 format

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "requestId": self.request_id,
            "timestamp": self.timestamp,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.instance:
            result["instance"] = self.instance
        return result


class ErrorTypes:
    """Error type URIs matching Node.js ErrorTypes from auth.ts.

    These are URI references that identify the error type.
    Clients can use these for programmatic error handling.
    """

    INVALID_CREDENTIALS = "/errors/invalid-credentials"
    UNAUTHORIZED = "/errors/unauthorized"
    FORBIDDEN = "/errors/forbidden"
    NOT_FOUND = "/errors/not-found"
    VALIDATION_ERROR = "/errors/validation-error"
    CONFLICT = "/errors/conflict"
    INTERNAL_ERROR = "/errors/internal-error"
    SERVICE_UNAVAILABLE = "/errors/service-unavailable"

    # Additional types for Python service
    INVALID_FILE_FORMAT = "/errors/invalid-file-format"
    FILE_TOO_LARGE = "/errors/file-too-large"


def create_error(
    error_type: str,
    title: str,
    status: int,
    detail: Optional[str] = None,
    instance: Optional[str] = None
) -> dict:
    """Create a ProblemDetail dict for HTTPException.detail.

    Args:
        error_type: Error type URI (use ErrorTypes constants)
        title: Human-readable error title
        status: HTTP status code
        detail: Detailed explanation
        instance: Request path

    Returns:
        Dict suitable for HTTPException(detail=...)

    Example:
        raise HTTPException(
            status_code=404,
            detail=create_error(
                error_type=ErrorTypes.NOT_FOUND,
                title="Paper Not Found",
                detail="Paper with ID 123 does not exist",
                instance="/api/papers/123"
            )
        )
    """
    problem = ProblemDetail(
        type=error_type,
        title=title,
        status=status,
        detail=detail,
        instance=instance
    )
    return problem.to_dict()


# Common error creators (matching Node.js Errors object)
class Errors:
    """Convenience error creators matching Node.js errorHandler.ts."""

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> dict:
        return create_error(ErrorTypes.UNAUTHORIZED, "Unauthorized", 401, message)

    @staticmethod
    def forbidden(message: str = "Forbidden") -> dict:
        return create_error(ErrorTypes.FORBIDDEN, "Forbidden", 403, message)

    @staticmethod
    def not_found(message: str = "Not Found") -> dict:
        return create_error(ErrorTypes.NOT_FOUND, "Not Found", 404, message)

    @staticmethod
    def validation(message: str = "Validation Error") -> dict:
        return create_error(ErrorTypes.VALIDATION_ERROR, "Validation Error", 400, message)

    @staticmethod
    def conflict(message: str = "Conflict") -> dict:
        return create_error(ErrorTypes.CONFLICT, "Conflict", 409, message)

    @staticmethod
    def internal(message: str = "Internal Server Error") -> dict:
        return create_error(ErrorTypes.INTERNAL_ERROR, "Internal Server Error", 500, message)

    @staticmethod
    def service_unavailable(message: str = "Service Unavailable") -> dict:
        return create_error(ErrorTypes.SERVICE_UNAVAILABLE, "Service Unavailable", 503, message)

    @staticmethod
    def invalid_credentials(message: str = "Invalid credentials") -> dict:
        return create_error(ErrorTypes.INVALID_CREDENTIALS, "Invalid credentials", 401, message)