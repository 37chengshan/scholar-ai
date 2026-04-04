"""Test RFC 7807 error format consistency.

Verifies that Python error format matches Node.js implementation.
"""

import pytest
from app.utils.problem_detail import Errors, create_error, ErrorTypes, ProblemDetail


def test_error_format_has_required_fields():
    """Verify RFC 7807 format has all required fields."""
    error = Errors.not_found("Test resource")
    
    assert "type" in error
    assert "title" in error
    assert "status" in error
    assert error["status"] == 404
    assert error["type"] == "/errors/not-found"


def test_error_format_matches_nodejs():
    """Verify Python error format matches Node.js implementation.
    
    Both should have: type, title, status, detail, requestId, timestamp
    """
    error = create_error(
        error_type=ErrorTypes.NOT_FOUND,
        title="Not Found",
        status=404,
        detail="Resource not found"
    )
    
    required_fields = ["type", "title", "status", "detail", "requestId", "timestamp"]
    for field in required_fields:
        assert field in error, f"Missing field: {field}"


def test_unauthorized_error():
    """Test unauthorized error helper."""
    error = Errors.unauthorized("Invalid token")
    
    assert error["status"] == 401
    assert error["type"] == "/errors/unauthorized"
    assert error["detail"] == "Invalid token"


def test_forbidden_error():
    """Test forbidden error helper."""
    error = Errors.forbidden("Access denied")
    
    assert error["status"] == 403
    assert error["type"] == "/errors/forbidden"
    assert error["detail"] == "Access denied"


def test_not_found_error():
    """Test not found error helper."""
    error = Errors.not_found("Paper not found")
    
    assert error["status"] == 404
    assert error["type"] == "/errors/not-found"
    assert error["detail"] == "Paper not found"


def test_validation_error():
    """Test validation error helper."""
    error = Errors.validation("Invalid email format")
    
    assert error["status"] == 400
    assert error["type"] == "/errors/validation-error"
    assert error["detail"] == "Invalid email format"


def test_conflict_error():
    """Test conflict error helper."""
    error = Errors.conflict("Email already exists")
    
    assert error["status"] == 409
    assert error["type"] == "/errors/conflict"
    assert error["detail"] == "Email already exists"


def test_internal_error():
    """Test internal server error helper."""
    error = Errors.internal("Database connection failed")
    
    assert error["status"] == 500
    assert error["type"] == "/errors/internal-error"
    assert error["detail"] == "Database connection failed"


def test_service_unavailable_error():
    """Test service unavailable error helper."""
    error = Errors.service_unavailable("Redis unavailable")
    
    assert error["status"] == 503
    assert error["type"] == "/errors/service-unavailable"
    assert error["detail"] == "Redis unavailable"


def test_problem_detail_to_dict():
    """Test ProblemDetail to_dict method."""
    problem = ProblemDetail(
        type=ErrorTypes.VALIDATION_ERROR,
        title="Validation Error",
        status=400,
        detail="Field is required",
        instance="/api/papers"
    )
    
    result = problem.to_dict()
    
    assert result["type"] == "/errors/validation-error"
    assert result["title"] == "Validation Error"
    assert result["status"] == 400
    assert result["detail"] == "Field is required"
    assert result["instance"] == "/api/papers"
    assert "requestId" in result
    assert "timestamp" in result


def test_error_types_match_nodejs():
    """Verify ErrorTypes match Node.js ErrorTypes."""
    # These should match the Node.js errorHandler.ts implementation
    assert ErrorTypes.INVALID_CREDENTIALS == "/errors/invalid-credentials"
    assert ErrorTypes.UNAUTHORIZED == "/errors/unauthorized"
    assert ErrorTypes.FORBIDDEN == "/errors/forbidden"
    assert ErrorTypes.NOT_FOUND == "/errors/not-found"
    assert ErrorTypes.VALIDATION_ERROR == "/errors/validation-error"
    assert ErrorTypes.CONFLICT == "/errors/conflict"
    assert ErrorTypes.INTERNAL_ERROR == "/errors/internal-error"
    assert ErrorTypes.SERVICE_UNAVAILABLE == "/errors/service-unavailable"


def test_error_includes_request_id():
    """Verify errors include unique request IDs."""
    error1 = Errors.not_found("Test 1")
    error2 = Errors.not_found("Test 2")
    
    assert "requestId" in error1
    assert "requestId" in error2
    assert error1["requestId"] != error2["requestId"]


def test_error_includes_timestamp():
    """Verify errors include ISO 8601 timestamp."""
    error = Errors.not_found("Test")
    
    assert "timestamp" in error
    # Timestamp should end with Z (UTC)
    assert error["timestamp"].endswith("Z")