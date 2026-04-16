"""Global exception handler for Python service.

Provides RFC 7807 Problem Detail format for all errors:
- Validation errors (RequestValidationError)
- HTTP exceptions (HTTPException)
- Generic exceptions (catch-all for unhandled errors)

Matches Node.js errorHandler.ts implementation.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger
import uuid
from typing import Optional


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with RFC 7807 format.

    Args:
        request: FastAPI request object
        exc: Validation error with field-level errors

    Returns:
        JSONResponse with RFC 7807 ProblemDetail
    """
    errors = exc.errors()
    # Format validation errors as readable string
    detail = "; ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors])

    problem = ProblemDetail(
        type=ErrorTypes.VALIDATION_ERROR,
        title="Validation Error",
        status=status.HTTP_400_BAD_REQUEST,
        detail=detail,
        instance=str(request.url.path)
    )

    logger.warning(
        "Validation error",
        path=request.url.path,
        errors=errors,
        request_id=problem.request_id
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": problem.to_dict()}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with RFC 7807 format.

    Args:
        request: FastAPI request object
        exc: HTTPException

    Returns:
        JSONResponse with RFC 7807 ProblemDetail
    """
    request_id = str(uuid.uuid4())

    # Extract error details from HTTPException
    error_detail = exc.detail
    error_type = ErrorTypes.INTERNAL_ERROR
    error_title = "Error"

    # If detail is already a ProblemDetail dict, use it
    if isinstance(error_detail, dict):
        # It's already formatted as ProblemDetail
        error_type = error_detail.get("type", ErrorTypes.INTERNAL_ERROR)
        error_title = error_detail.get("title", "Error")
        error_detail_text = error_detail.get("detail")
    else:
        error_detail_text = str(error_detail) if error_detail else None

        # Map status code to error type
        if exc.status_code == 401:
            error_type = ErrorTypes.UNAUTHORIZED
            error_title = "Unauthorized"
        elif exc.status_code == 403:
            error_type = ErrorTypes.FORBIDDEN
            error_title = "Forbidden"
        elif exc.status_code == 404:
            error_type = ErrorTypes.NOT_FOUND
            error_title = "Not Found"
        elif exc.status_code == 409:
            error_type = ErrorTypes.CONFLICT
            error_title = "Conflict"

    problem = ProblemDetail(
        type=error_type,
        title=error_title,
        status=exc.status_code,
        detail=error_detail_text,
        instance=str(request.url.path)
    )
    problem.request_id = request_id

    logger.warning(
        f"HTTP exception: {exc.status_code}",
        path=request.url.path,
        detail=error_detail_text,
        request_id=request_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": problem.to_dict()}
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions.

    Logs error with request context and returns RFC 7807 format.
    Does NOT expose internal error details to client.

    Args:
        request: FastAPI request object
        exc: Any unhandled exception

    Returns:
        JSONResponse with RFC 7807 ProblemDetail
    """
    request_id = str(uuid.uuid4())

    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )

    problem = ProblemDetail(
        type=ErrorTypes.INTERNAL_ERROR,
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url.path)
    )
    problem.request_id = request_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": problem.to_dict()}
    )


def setup_error_handlers(app: FastAPI, include_generic: bool = False) -> None:
    """Register all error handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
        include_generic: Whether to include generic exception handler.
            Set to False in development to see tracebacks, True in production.

    Example:
        app = FastAPI()
        setup_error_handlers(app)
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    if include_generic:
        app.add_exception_handler(Exception, generic_exception_handler)


__all__ = [
    "validation_exception_handler",
    "http_exception_handler",
    "generic_exception_handler",
    "setup_error_handlers",
]