"""
Pytest fixtures and configuration for backend-python tests.
"""

import os
from typing import AsyncGenerator, Generator

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

# Set test environment before importing app
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-public-key")


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create a test FastAPI application."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_internal_token() -> str:
    """Generate a mock internal service token for testing."""
    # This is a placeholder - actual implementation would use JWT signing
    return "test-internal-token"


@pytest.fixture
def mock_auth_headers(mock_internal_token: str) -> dict:
    """Return headers with internal auth token for protected endpoints."""
    return {
        "Authorization": f"Bearer {mock_internal_token}",
        "X-Internal-Service": "test-service",
    }
