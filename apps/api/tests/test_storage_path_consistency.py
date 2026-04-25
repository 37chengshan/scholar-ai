from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.import_file_service import build_upload_storage_key
from app.services.upload_session_service import UploadSessionService
from app.workers.import_worker_helpers import compute_hash


def test_storage_key_format_is_shared_across_upload_paths():
    service = UploadSessionService()
    storage_key = build_upload_storage_key("user-1", "imp-1")

    assert storage_key == service._upload_storage_key("user-1", "imp-1")
    assert storage_key == "uploads/user-1/" + storage_key.split("uploads/user-1/")[1]
    assert storage_key.endswith("/imp-1.pdf")


@pytest.mark.asyncio
async def test_compute_hash_uses_settings_local_storage_path(tmp_path: Path):
    storage_key = "uploads/user-1/2026/04/25/imp-1.pdf"
    file_path = tmp_path / storage_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"%PDF-1.4\nhello\n%%EOF")

    with patch("app.workers.import_worker_helpers.settings.LOCAL_STORAGE_PATH", str(tmp_path)):
        digest = await compute_hash(storage_key)

    assert digest


@pytest.mark.asyncio
async def test_upload_session_completion_writes_to_canonical_upload_prefix(tmp_path: Path):
    service = UploadSessionService()
    db = AsyncMock()

    part_content = b"%PDF-1.4\nhello\n%%EOF"
    part_dir = tmp_path / "sessions" / "us_1" / "parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    (part_dir / "1.part").write_bytes(part_content)

    session = SimpleNamespace(
        id="us_1",
        import_job_id="imp_1",
        user_id="user-1",
        knowledge_base_id="kb-1",
        filename="paper.pdf",
        mime_type="application/pdf",
        storage_key=None,
        file_sha256=None,
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
    job = SimpleNamespace(id="imp_1")

    captured_storage_key = None

    async def _capture_set_file_info(**kwargs):
        nonlocal captured_storage_key
        captured_storage_key = kwargs.get("storage_key")

    with (
        patch("app.services.upload_session_service.settings.LOCAL_STORAGE_PATH", str(tmp_path)),
        patch.object(service, "get_session", AsyncMock(return_value=session)),
        patch.object(service._import_job_service, "get_job", AsyncMock(return_value=job)),
        patch.object(service._import_job_service, "set_file_info", AsyncMock(side_effect=_capture_set_file_info)),
        patch("app.services.upload_session_service.process_import_job") as mock_process,
    ):
        result = await service.complete_session("us_1", "user-1", db)

    assert captured_storage_key is not None
    assert captured_storage_key.startswith("uploads/user-1/")
    assert (tmp_path / captured_storage_key).exists()
    mock_process.delay.assert_called_once_with("imp_1")