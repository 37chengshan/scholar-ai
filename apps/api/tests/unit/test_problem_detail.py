import pytest
from app.utils.problem_detail import (
    ProblemDetail,
    ErrorTypes,
    create_error,
    Errors
)


class TestProblemDetail:
    """Tests for ProblemDetail dataclass."""

    def test_problem_detail_creation(self):
        """Test basic ProblemDetail creation."""
        problem = ProblemDetail(
            type=ErrorTypes.NOT_FOUND,
            title="Not Found",
            status=404,
            detail="Resource not found",
            instance="/api/papers/123"
        )

        assert problem.type == "/errors/not-found"
        assert problem.title == "Not Found"
        assert problem.status == 404
        assert problem.detail == "Resource not found"
        assert problem.instance == "/api/papers/123"
        assert problem.request_id is not None
        assert problem.timestamp is not None

    def test_problem_detail_auto_generates_request_id(self):
        """Test that request_id is auto-generated if not provided."""
        problem = ProblemDetail(
            type=ErrorTypes.INTERNAL_ERROR,
            title="Error",
            status=500
        )

        assert problem.request_id is not None
        assert len(problem.request_id) == 36  # UUID format

    def test_problem_detail_auto_generates_timestamp(self):
        """Test that timestamp is auto-generated in ISO 8601 format."""
        problem = ProblemDetail(
            type=ErrorTypes.INTERNAL_ERROR,
            title="Error",
            status=500
        )

        assert problem.timestamp is not None
        assert problem.timestamp.endswith("Z")  # UTC

    def test_to_dict_includes_all_fields(self):
        """Test to_dict() includes all required fields."""
        problem = ProblemDetail(
            type=ErrorTypes.VALIDATION_ERROR,
            title="Validation Error",
            status=400,
            detail="Invalid input"
        )

        result = problem.to_dict()

        assert result["type"] == "/errors/validation-error"
        assert result["title"] == "Validation Error"
        assert result["status"] == 400
        assert result["detail"] == "Invalid input"
        assert "requestId" in result
        assert "timestamp" in result


class TestErrorTypes:
    """Tests for ErrorTypes constants."""

    def test_error_types_match_nodejs(self):
        """Test that error types match Node.js implementation."""
        # These must match scholar-ai/backend-node/src/types/auth.ts
        assert ErrorTypes.INVALID_CREDENTIALS == "/errors/invalid-credentials"
        assert ErrorTypes.UNAUTHORIZED == "/errors/unauthorized"
        assert ErrorTypes.FORBIDDEN == "/errors/forbidden"
        assert ErrorTypes.NOT_FOUND == "/errors/not-found"
        assert ErrorTypes.VALIDATION_ERROR == "/errors/validation-error"
        assert ErrorTypes.CONFLICT == "/errors/conflict"
        assert ErrorTypes.INTERNAL_ERROR == "/errors/internal-error"
        assert ErrorTypes.SERVICE_UNAVAILABLE == "/errors/service-unavailable"


class TestCreateError:
    """Tests for create_error helper."""

    def test_create_error_returns_dict(self):
        """Test that create_error returns a dictionary."""
        error = create_error(
            error_type=ErrorTypes.NOT_FOUND,
            title="Paper Not Found",
            status=404,
            detail="Paper 123 does not exist",
            instance="/api/papers/123"
        )

        assert isinstance(error, dict)
        assert error["type"] == "/errors/not-found"
        assert error["title"] == "Paper Not Found"
        assert error["status"] == 404
        assert error["detail"] == "Paper 123 does not exist"
        assert error["instance"] == "/api/papers/123"

    def test_create_error_minimal(self):
        """Test create_error with minimal args."""
        error = create_error(
            error_type=ErrorTypes.INTERNAL_ERROR,
            title="Error",
            status=500
        )

        assert error["type"] == "/errors/internal-error"
        assert error["title"] == "Error"
        assert error["status"] == 500
        assert "detail" not in error  # Optional


class TestErrors:
    """Tests for Errors convenience class."""

    def test_unauthorized_error(self):
        error = Errors.unauthorized("Token expired")
        assert error["type"] == "/errors/unauthorized"
        assert error["status"] == 401

    def test_not_found_error(self):
        error = Errors.not_found("Paper not found")
        assert error["type"] == "/errors/not-found"
        assert error["status"] == 404

    def test_validation_error(self):
        error = Errors.validation("Invalid email format")
        assert error["type"] == "/errors/validation-error"
        assert error["status"] == 400