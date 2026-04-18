"""Unit tests for UploadSessionService."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.upload_session import CreateUploadSessionRequest
from app.services.upload_session_service import UploadSessionService


@pytest.mark.asyncio
async def test_create_session_returns_instant_import_when_hash_matches():
    service = UploadSessionService()
    db = AsyncMock()

    job = SimpleNamespace(
        id="imp_1",
        source_type="local_file",
        status="created",
        user_id="u1",
        knowledge_base_id="kb1",
    )
    matched = SimpleNamespace(id="imp_old", paper_id="paper_1", file_sha256="abc", storage_key="k")

    with (
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service, "_find_completed_match", AsyncMock(return_value=matched)),
        patch.object(service, "_apply_instant_reuse", AsyncMock()),
    ):
        result = await service.create_session(
            "imp_1",
            "u1",
            CreateUploadSessionRequest(
                filename="a.pdf",
                sizeBytes=1024,
                chunkSize=512,
                sha256="abc",
                mimeType="application/pdf",
            ),
            db,
        )

    assert result["instantImport"] is True
    assert result["paperId"] == "paper_1"


@pytest.mark.asyncio
async def test_register_part_persists_chunk_and_updates_state(tmp_path: Path):
    service = UploadSessionService()
    db = AsyncMock()

    session = SimpleNamespace(
        id="us_1",
        import_job_id="imp_1",
        user_id="u1",
        knowledge_base_id="kb1",
        filename="paper.pdf",
        mime_type="application/pdf",
        file_sha256=None,
        size_bytes=10,
        chunk_size=5,
        total_parts=2,
        uploaded_parts=[],
        uploaded_bytes=0,
        status="created",
        error_message=None,
        expires_at=None,
        completed_at=None,
        updated_at=None,
    )

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
    ):
        state = await service.register_part("us_1", "u1", 1, b"12345", db)

    assert state["uploadedParts"] == [1]
    assert state["status"] == "uploading"
    assert (tmp_path / "sessions" / "us_1" / "parts" / "1.part").exists()


@pytest.mark.asyncio
async def test_complete_session_merges_parts_and_queues_import(tmp_path: Path):
    service = UploadSessionService()
    db = AsyncMock()

    part_content = b"%PDF-1.4\nhello\n%%EOF"
    expected_hash = hashlib.sha256(part_content).hexdigest()

    part_dir = tmp_path / "sessions" / "us_2" / "parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    (part_dir / "1.part").write_bytes(part_content)

    session = SimpleNamespace(
        id="us_2",
        import_job_id="imp_2",
        user_id="u1",
        knowledge_base_id="kb1",
        filename="paper.pdf",
        mime_type="application/pdf",
        storage_key=None,
        file_sha256=expected_hash,
        size_bytes=len(part_content),
        chunk_size=len(part_content),
        total_parts=1,
        uploaded_parts=[1],
        uploaded_bytes=len(part_content),
        status="uploading",
        error_message=None,
        expires_at=None,
        completed_at=None,
        updated_at=None,
    )
    job = SimpleNamespace(id="imp_2")

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service._import_job_service, "set_file_info", AsyncMock()),
        patch("app.services.upload_session_service.process_import_job") as mock_process,
    ):
        result = await service.complete_session("us_2", "u1", db)

    assert result["status"] == "completed"
    assert session.storage_key is not None
    mock_process.delay.assert_called_once_with("imp_2")


@pytest.mark.asyncio
async def test_complete_session_is_idempotent_when_already_completed(tmp_path: Path):
    service = UploadSessionService()
    db = AsyncMock()

    session = SimpleNamespace(
        id="us_done",
        import_job_id="imp_done",
        user_id="u1",
        knowledge_base_id="kb1",
        filename="paper.pdf",
        mime_type="application/pdf",
        storage_key="uploads/u1/2026/04/17/imp_done.pdf",
        file_sha256="abc",
        size_bytes=100,
        chunk_size=50,
        total_parts=2,
        uploaded_parts=[1, 2],
        uploaded_bytes=100,
        status="completed",
        error_message=None,
        expires_at=None,
        completed_at=None,
        updated_at=None,
    )

    with (
        patch.dict("os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
        patch.object(service._import_job_service, "set_file_info", AsyncMock()) as mock_set_file,
        patch("app.services.upload_session_service.process_import_job") as mock_process,
    ):
        result = await service.complete_session("us_done", "u1", db)

    assert result["status"] == "completed"
    mock_set_file.assert_not_called()
    mock_process.delay.assert_not_called()


@pytest.mark.asyncio
async def test_create_session_rejects_queued_job_status():
    service = UploadSessionService()
    db = AsyncMock()

    job = SimpleNamespace(
        id="imp_q",
        source_type="local_file",
        status="queued",
        user_id="u1",
        knowledge_base_id="kb1",
    )

    with patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)):
        with pytest.raises(ValueError, match="does not allow upload session"):
            await service.create_session(
                "imp_q",
                "u1",
                CreateUploadSessionRequest(
                    filename="a.pdf",
                    sizeBytes=1024,
                    chunkSize=512,
                    sha256="abc",
                    mimeType="application/pdf",
                ),
                db,
            )
