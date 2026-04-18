"""Runtime preflight checks for API startup and CI validation."""

from __future__ import annotations

import platform
import sys
from importlib import import_module
from typing import Dict, List

from app.config import settings


def _check_python_version() -> Dict[str, str]:
    current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    required = f"{settings.REQUIRED_PYTHON_MAJOR}.{settings.REQUIRED_PYTHON_MINOR}"
    passed = (
        sys.version_info.major == settings.REQUIRED_PYTHON_MAJOR
        and sys.version_info.minor == settings.REQUIRED_PYTHON_MINOR
    )
    return {
        "status": "pass" if passed else "fail",
        "current": current,
        "required": required,
        "platform": platform.platform(),
    }


def _check_import(module_name: str) -> Dict[str, str]:
    try:
        import_module(module_name)
        return {"status": "pass"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "fail", "error": str(exc)}


def run_preflight(strict: bool = False) -> Dict[str, object]:
    """Run preflight checks and optionally fail in strict mode."""
    checks = {
        "python": _check_python_version(),
        "fastapi": _check_import("fastapi"),
        "sqlalchemy": _check_import("sqlalchemy"),
        "pydantic": _check_import("pydantic"),
        "uvicorn": _check_import("uvicorn"),
    }

    failures: List[str] = [name for name, result in checks.items() if result["status"] != "pass"]
    status = "pass" if not failures else "fail"

    if strict and failures:
        raise RuntimeError(f"Preflight failed: {', '.join(failures)}")

    return {
        "status": status,
        "profile": settings.RUNTIME_PROFILE,
        "ai_startup_mode": settings.AI_STARTUP_MODE,
        "checks": checks,
        "failures": failures,
    }
