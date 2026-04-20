"""Integration-style lifecycle tests for upload sessions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.upload_session import UploadSession
from app.schemas.upload_session import CreateUploadSessionRequest
from app.services.upload_session_service import UploadSessionService


def _make_job(status: str = "created") -> SimpleNamespace:
    return SimpleNamespace(
        id="imp_1",
        source_type="local_file",
        status=status,
        user_id="user-1",
        knowledge_base_id="kb-1",
        next_action=None,
        updated_at=None,
    )


@pytest.mark.asyncio
async def test_upload_session_lifecycle_create_upload_complete(tmp_path: Path):
    service = UploadSessionService()
    captured: dict[str, UploadSession] = {}
    combined_content = b"%PDF-1.4\nhello world\n%%EOF"
    chunk_size = len(combined_content) // 2
    payload = CreateUploadSessionRequest(
        filename="paper.pdf",
        sizeBytes=len(combined_content),
        chunkSize=chunk_size,
        sha256=hashlib.sha256(combined_content).hexdigest(),
        mimeType="application/pdf",
    )
    job = _make_job()

    def _capture_add(obj):
        if isinstance(obj, UploadSession):
            captured["session"] = obj

    async def _refresh(obj):
        if isinstance(obj, UploadSession):
            obj.id = obj.id or "us_test_1"
            obj.expires_at = obj.expires_at or datetime.now(timezone.utc)

    db = SimpleNamespace(
        add=MagicMock(side_effect=_capture_add),
        commit=AsyncMock(),
        refresh=AsyncMock(side_effect=_refresh),
    )

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service, "_find_completed_match", AsyncMock(return_value=None)),
        patch.object(service, "_find_active_session", AsyncMock(return_value=None)),
    ):
        created = await service.create_session("imp_1", "user-1", payload, db)

    assert created["instantImport"] is False
    assert created["session"]["uploadSessionId"] == "us_test_1"
    assert created["session"]["missingParts"] == [1, 2]

    session = captured["session"]
    chunks = [
        combined_content[:chunk_size],
        combined_content[chunk_size:],
    ]

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
    ):
        for index, chunk in enumerate(chunks, start=1):
            state = await service.register_part(session.id, "user-1", index, chunk, db)

    assert state["status"] == "uploading"
    assert state["missingParts"] == []
    assert state["uploadedParts"] == [1, 2]

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service._import_job_service, "set_file_info", AsyncMock()) as mock_set_file_info,
        patch("app.services.upload_session_service.process_import_job") as mock_process_import_job,
    ):
        completed = await service.complete_session(session.id, "user-1", db)

    assert completed["status"] == "completed"
    assert completed["missingParts"] == []
    assert session.storage_key is not None
    mock_set_file_info.assert_awaited_once()
    assert mock_set_file_info.await_args.kwargs == {
        "job": job,
        "storage_key": session.storage_key,
        "sha256": payload.sha256,
        "size_bytes": len(combined_content),
        "filename": "paper.pdf",
        "mime_type": "application/pdf",
        "db": db,
    }
    mock_process_import_job.delay.assert_called_once_with("imp_1")

    merged_file = tmp_path / session.storage_key
    assert merged_file.exists()
    assert merged_file.read_bytes() == combined_content


@pytest.mark.asyncio
async def test_create_session_returns_existing_active_session_state():
    service = UploadSessionService()
    db = SimpleNamespace(add=MagicMock(), commit=AsyncMock(), refresh=AsyncMock())
    job = _make_job()
    existing_session = SimpleNamespace(
        id="us_existing",
        import_job_id="imp_1",
        status="uploading",
        chunk_size=4,
        total_parts=3,
        uploaded_parts=[1],
        uploaded_bytes=4,
        size_bytes=12,
        expires_at=datetime.now(timezone.utc),
        completed_at=None,
    )

    with (
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service, "_find_completed_match", AsyncMock(return_value=None)),
        patch.object(service, "_find_active_session", AsyncMock(return_value=existing_session)),
    ):
        result = await service.create_session(
            "imp_1",
            "user-1",
            CreateUploadSessionRequest(
                filename="paper.pdf",
                sizeBytes=12,
                chunkSize=4,
                sha256=None,
                mimeType="application/pdf",
            ),
            db,
        )

    assert result["instantImport"] is False
    assert result["session"]["uploadSessionId"] == "us_existing"
    assert result["session"]["missingParts"] == [2, 3]


@pytest.mark.asyncio
async def test_abort_session_marks_session_aborted_and_prevents_completion():
    service = UploadSessionService()
    db = SimpleNamespace(add=MagicMock(), commit=AsyncMock(), refresh=AsyncMock())
    session = SimpleNamespace(
        id="us_abort",
        import_job_id="imp_1",
        status="created",
        chunk_size=5,
        total_parts=2,
        uploaded_parts=[],
        uploaded_bytes=0,
        size_bytes=10,
        file_sha256=None,
        filename="paper.pdf",
        mime_type="application/pdf",
        expires_at=datetime.now(timezone.utc),
        completed_at=None,
        updated_at=None,
    )

    with patch.object(service, "get_session", AsyncMock(return_value=session)):
        result = await service.abort_session("us_abort", "user-1", db)

    assert result["status"] == "aborted"
    assert session.status == "aborted"

    with patch.object(service, "get_session", AsyncMock(return_value=session)):
        with pytest.raises(ValueError, match="Upload session is aborted"):
            await service.complete_session("us_abort", "user-1", db)

    with patch.object(service, "get_session", AsyncMock(return_value=session)):
        with pytest.raises(ValueError, match="Upload session is aborted"):
            await service.register_part("us_abort", "user-1", 1, b"chunk", db)