"""Preflight check tests."""

from app.utils.preflight import run_preflight


def test_preflight_reports_python_runtime():
    result = run_preflight(strict=False)
    assert "python" in result["checks"]
    assert "status" in result


def test_preflight_contains_required_dependency_checks():
    result = run_preflight(strict=False)
    checks = result["checks"]
    for key in ["fastapi", "sqlalchemy", "pydantic", "uvicorn"]:
        assert key in checks
        assert checks[key]["status"] in {"pass", "fail"}
