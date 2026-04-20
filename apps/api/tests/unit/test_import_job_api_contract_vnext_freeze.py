"""Contract tests for ImportJob API freeze fields."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.imports.jobs import upload_file_to_job


@pytest.mark.asyncio
async def test_upload_file_endpoint_marks_fallback_path_mode(tmp_path):
    job = SimpleNamespace(
        id="job-1",
        source_type="local_file",
        status="created",
    )

    db = AsyncMock()

    fake_upload = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.4\nbody\n%%EOF"))

    service_mock = MagicMock()
    service_mock.get_job = AsyncMock(return_value=job)
    service_mock.set_file_info = AsyncMock(return_value=None)

    with patch("app.api.imports.jobs.ImportJobService", return_value=service_mock), patch.dict(
        "os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}
    ), patch("app.workers.import_worker.process_import_job") as worker_mock:
        worker_mock.delay = MagicMock(return_value=None)

        response = await upload_file_to_job(
            job_id="job-1",
            file=fake_upload,
            user_id="user-1",
            db=db,
        )

    assert response.success is True
    assert response.data["pathMode"] == "fallback_small_file_only"
    assert response.data["status"] == "queued"
    assert response.data["stage"] == "uploaded"


@pytest.mark.asyncio
async def test_upload_file_rejects_non_local_file_job(tmp_path):
    job = SimpleNamespace(
        id="job-2",
        source_type="doi",
        status="created",
    )

    db = AsyncMock()
    fake_upload = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.4\nbody\n%%EOF"))

    service_mock = MagicMock()
    service_mock.get_job = AsyncMock(return_value=job)

    with patch("app.api.imports.jobs.ImportJobService", return_value=service_mock), patch.dict(
        "os.environ", {"LOCAL_STORAGE_PATH": str(tmp_path)}
    ):
        with pytest.raises(HTTPException) as exc:
            await upload_file_to_job(
                job_id="job-2",
                file=fake_upload,
                user_id="user-1",
                db=db,
            )

    assert exc.value.status_code == 400
