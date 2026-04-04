"""Global exception handler for Python service.

Provides RFC 7807 Problem Detail format for all errors:
- Validation errors (RequestValidationError)
- Generic exceptions (catch-all for unhandled errors)

Matches Node.js errorHandler.ts implementation.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger
import uuid


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