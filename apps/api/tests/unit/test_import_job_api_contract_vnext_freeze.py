"""Contract tests for ImportJob API freeze fields."""

from io import BytesIO
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.imports.jobs import (
    CreateImportRequest,
    create_import_job,
    list_import_jobs,
    upload_file_to_job,
)


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
async def test_create_import_job_enqueues_external_sources():
    kb = SimpleNamespace(id="kb-1", user_id="user-1")
    job = SimpleNamespace(
        id="job-external-1",
        status="queued",
        stage="resolving_source",
        progress=0,
        next_action=None,
    )

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: kb)

    service_mock = MagicMock()
    service_mock.create_job = AsyncMock(return_value=job)

    with patch("app.api.imports.jobs.ImportJobService", return_value=service_mock), patch(
        "app.workers.import_worker.process_import_job"
    ) as worker_mock:
        worker_mock.delay = MagicMock(return_value=None)

        response = await create_import_job(
            kb_id="kb-1",
            request=CreateImportRequest(
                sourceType="semantic_scholar",
                payload={"input": "paper-123", "s2PaperId": "paper-123"},
            ),
            user_id="user-1",
            db=db,
        )

    assert response.success is True
    assert response.data["importJobId"] == "job-external-1"
    worker_mock.delay.assert_called_once_with("job-external-1")


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


@pytest.mark.asyncio
async def test_list_import_jobs_keeps_dedupe_contract_fields():
    now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    job = SimpleNamespace(
        id="job-dedupe-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        status="awaiting_user_action",
        stage="awaiting_dedupe_decision",
        progress=35,
        next_action={
            "type": "awaiting_dedupe_decision",
            "matchedPaperId": "paper-42",
            "matchType": "sha256",
        },
        retry_count=0,
        version=None,
        source_ref_raw="paper.pdf",
        source_ref_normalized="paper.pdf",
        external_ids={},
        resolved_title="Imported Paper",
        resolved_authors=["A. Author"],
        resolved_year=2025,
        resolved_venue="ACL",
        dedupe_status="match_found",
        dedupe_match_paper_id="paper-42",
        dedupe_match_type="sha256",
        dedupe_decision=None,
        storage_key=None,
        file_sha256=None,
        size_bytes=None,
        paper_id=None,
        processing_task_id=None,
        processing_task_status=None,
        processing_task_checkpoint_stage=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
    )

    db = AsyncMock()
    service_mock = MagicMock()
    service_mock.list_jobs = AsyncMock(return_value=[job])

    with patch("app.api.imports.jobs.ImportJobService", return_value=service_mock):
        response = await list_import_jobs(
            knowledgeBaseId="kb-1",
            status=None,
            limit=50,
            offset=0,
            user_id="user-1",
            db=db,
        )

    assert response.success is True
    listed = response.data["jobs"][0]
    assert listed["dedupe"]["matchedPaperId"] == "paper-42"
    assert listed["dedupe"]["matchType"] == "sha256"
    assert listed["preview"]["authors"] == ["A. Author"]
    assert listed["source"]["normalizedRef"] == "paper.pdf"
    assert listed["nextAction"]["matchedPaperId"] == "paper-42"
