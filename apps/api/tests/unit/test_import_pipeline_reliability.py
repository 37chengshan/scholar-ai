"""Unit tests for import pipeline reliability fixes.

Covers:
- dedupe decision re-queue behavior
- batch local file upload partial success behavior
"""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.api.imports.batches import upload_batch_local_files
from app.api.imports.dedupe import DedupeDecisionRequest, submit_dedupe_decision
from app.models.import_batch import ImportBatch
from app.models.import_job import ImportJob


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


@pytest.mark.asyncio
async def test_submit_dedupe_decision_requeues_for_force_new_paths():
    db = AsyncMock()
    job = ImportJob(
        id="imp_1234567890abcdef123456",
        user_id="user-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        source_ref_raw="paper.pdf",
        status="awaiting_user_action",
        stage="awaiting_dedupe_decision",
    )
    db.execute.side_effect = [_ScalarResult(job)]

    with patch("app.workers.import_worker.process_import_job.delay") as mock_delay:
        response = await submit_dedupe_decision(
            job_id=job.id,
            request=DedupeDecisionRequest(decision="force_new_paper"),
            user_id="user-1",
            db=db,
        )

    assert response.data["status"] == "queued"
    assert job.dedupe_decision == "force_new_paper"
    assert job.dedupe_status == "resolved"
    assert job.next_action is None
    mock_delay.assert_called_once_with(job.id)


@pytest.mark.asyncio
async def test_upload_batch_local_files_allows_partial_success():
    db = AsyncMock()
    now = datetime.now(timezone.utc)

    batch = ImportBatch(
        id="impb_batch123456",
        user_id="user-1",
        knowledge_base_id="kb-1",
        status="created",
        total_items=2,
        completed_items=0,
        failed_items=0,
        cancelled_items=0,
        created_at=now,
        updated_at=now,
    )

    job1 = ImportJob(
        id="imp_job000000000000000001",
        user_id="user-1",
        knowledge_base_id="kb-1",
        batch_id=batch.id,
        source_type="local_file",
        source_ref_raw="ok.pdf",
        status="created",
        stage="awaiting_input",
    )
    job2 = ImportJob(
        id="imp_job000000000000000002",
        user_id="user-1",
        knowledge_base_id="kb-1",
        batch_id=batch.id,
        source_type="local_file",
        source_ref_raw="missing.pdf",
        status="created",
        stage="awaiting_input",
    )

    db.execute.side_effect = [
        _ScalarResult(batch),
        _ScalarsResult([job1, job2]),
    ]

    files = [
        UploadFile(filename="ok.pdf", file=BytesIO(b"%PDF-1.4\nhello\n%%EOF")),
    ]
    manifest = (
        '[{"importJobId":"imp_job000000000000000001","filename":"ok.pdf"},'
        '{"importJobId":"imp_job000000000000000002","filename":"missing.pdf"}]'
    )

    mock_open = MagicMock()
    mock_open.__enter__.return_value.write = MagicMock()
    mock_open.__exit__.return_value = False

    with (
        patch("app.api.imports.batches.os.makedirs"),
        patch("app.api.imports.batches.open", return_value=mock_open),
        patch("app.workers.import_worker.process_import_job.delay") as mock_delay,
    ):
        response = await upload_batch_local_files(
            batch_id=batch.id,
            manifest=manifest,
            files=files,
            user_id="user-1",
            db=db,
        )

    assert response.data["batchJobId"] == batch.id
    assert response.data["acceptedCount"] == 1
    assert response.data["rejectedCount"] == 1
    assert response.data["accepted"][0]["importJobId"] == job1.id
    assert response.data["rejected"][0]["importJobId"] == job2.id
    mock_delay.assert_called_once_with(job1.id)


@pytest.mark.asyncio
async def test_upload_batch_local_files_marks_job_failed_when_enqueue_fails():
    db = AsyncMock()
    now = datetime.now(timezone.utc)

    batch = ImportBatch(
        id="impb_batch999999",
        user_id="user-1",
        knowledge_base_id="kb-1",
        status="created",
        total_items=1,
        completed_items=0,
        failed_items=0,
        cancelled_items=0,
        created_at=now,
        updated_at=now,
    )

    job = ImportJob(
        id="imp_job999999999999999999",
        user_id="user-1",
        knowledge_base_id="kb-1",
        batch_id=batch.id,
        source_type="local_file",
        source_ref_raw="queue-fail.pdf",
        status="created",
        stage="awaiting_input",
    )

    db.execute.side_effect = [
        _ScalarResult(batch),
        _ScalarsResult([job]),
    ]

    files = [
        UploadFile(filename="queue-fail.pdf", file=BytesIO(b"%PDF-1.4\nhello\n%%EOF")),
    ]
    manifest = '[{"importJobId":"imp_job999999999999999999","filename":"queue-fail.pdf"}]'

    mock_open = MagicMock()
    mock_open.__enter__.return_value.write = MagicMock()
    mock_open.__exit__.return_value = False

    with (
        patch("app.api.imports.batches.os.makedirs"),
        patch("app.api.imports.batches.open", return_value=mock_open),
        patch(
            "app.workers.import_worker.process_import_job.delay",
            side_effect=RuntimeError("broker unavailable"),
        ),
    ):
        response = await upload_batch_local_files(
            batch_id=batch.id,
            manifest=manifest,
            files=files,
            user_id="user-1",
            db=db,
        )

    assert response.data["acceptedCount"] == 0
    assert response.data["rejectedCount"] == 1
    assert response.data["rejected"][0]["importJobId"] == job.id
    assert job.status == "failed"
    assert job.error_code == "QUEUE_SUBMIT_FAILED"
