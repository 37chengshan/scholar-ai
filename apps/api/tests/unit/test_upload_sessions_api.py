"""Unit tests for upload sessions API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from app.api.imports.upload_sessions import router
from app.database import get_db
from app.middleware.auth import get_current_user_id


@pytest_asyncio.fixture
async def client():
    app = FastAPI()
    app.include_router(router)

    async def _fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_db] = _fake_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_upload_session_success(client):
    with patch(
        "app.api.imports.upload_sessions._service.create_session",
        AsyncMock(return_value={"instantImport": False, "session": {"uploadSessionId": "us_1"}}),
    ):
        response = await client.post(
            "/import-jobs/imp_1/upload-sessions",
            json={
                "filename": "paper.pdf",
                "sizeBytes": 100,
                "chunkSize": 10,
                "sha256": "abc",
                "mimeType": "application/pdf",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["session"]["uploadSessionId"] == "us_1"


@pytest.mark.asyncio
async def test_upload_part_validation_error(client):
    with patch(
        "app.api.imports.upload_sessions._service.register_part",
        AsyncMock(side_effect=ValueError("Part number out of range")),
    ):
        response = await client.put(
            "/upload-sessions/us_1/parts/99",
            content=b"abc",
            headers={"content-type": "application/octet-stream"},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_complete_upload_session_success(client):
    with patch(
        "app.api.imports.upload_sessions._service.complete_session",
        AsyncMock(return_value={"uploadSessionId": "us_1", "status": "completed"}),
    ):
        response = await client.post("/upload-sessions/us_1/complete")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_complete_upload_session_not_found_returns_404(client):
    with patch(
        "app.api.imports.upload_sessions._service.complete_session",
        AsyncMock(side_effect=ValueError("Upload session not found")),
    ):
        response = await client.post("/upload-sessions/us_missing/complete")

    assert response.status_code == 404
