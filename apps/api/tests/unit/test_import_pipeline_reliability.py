"""Unit tests for import pipeline reliability fixes.

Covers:
- dedupe decision re-queue behavior
- batch local file upload partial success behavior
- hash dedupe tolerates historical duplicate imports
- error persistence reloads a fresh ImportJob instance
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
from app.services.import_dedupe_service import ImportDedupeService
from app.services.import_job_service import ImportJobService
from app.workers.import_worker_helpers import _resolve_s2_paper_id_for_insert


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

    def first(self):
        return self._values[0] if self._values else None


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
        _ScalarResult(job),
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


@pytest.mark.asyncio
async def test_hash_dedupe_uses_latest_completed_match_without_requiring_uniqueness():
    db = AsyncMock()
    service = ImportDedupeService()

    old_job = ImportJob(
        id="imp_old_completed",
        user_id="user-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        source_ref_raw="old.pdf",
        status="completed",
        stage="completed",
        paper_id="paper-old",
    )
    new_job = ImportJob(
        id="imp_new_completed",
        user_id="user-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        source_ref_raw="new.pdf",
        status="completed",
        stage="completed",
        paper_id="paper-new",
    )
    db.execute.return_value = _ScalarsResult([new_job, old_job])

    match = await service._match_by_hash("sha256", "user-1", db)

    assert match is new_job


@pytest.mark.asyncio
async def test_cross_user_duplicate_s2_paper_id_is_omitted_before_insert():
    db = AsyncMock()
    db.execute.return_value = _ScalarResult("existing-paper")

    resolved = await _resolve_s2_paper_id_for_insert(db, "s2-duplicate")

    assert resolved is None


@pytest.mark.asyncio
async def test_fresh_s2_paper_id_is_preserved_before_insert():
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(None)

    resolved = await _resolve_s2_paper_id_for_insert(db, "s2-fresh")

    assert resolved == "s2-fresh"


@pytest.mark.asyncio
async def test_set_error_reloads_job_before_marking_failed():
    db = AsyncMock()
    service = ImportJobService()

    stale_job = ImportJob(
        id="imp_stale_job",
        user_id="user-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        source_ref_raw="stale.pdf",
        status="running",
        stage="dedupe_check",
    )
    fresh_job = ImportJob(
        id="imp_stale_job",
        user_id="user-1",
        knowledge_base_id="kb-1",
        source_type="local_file",
        source_ref_raw="fresh.pdf",
        status="running",
        stage="dedupe_check",
    )
    db.execute.return_value = _ScalarResult(fresh_job)

    updated = await service.set_error(
        stale_job,
        error_code="IMPORT_FAILED",
        error_message="boom",
        db=db,
    )

    assert updated is fresh_job
    assert fresh_job.status == "failed"
    assert fresh_job.stage == "failed"
    assert fresh_job.error_code == "IMPORT_FAILED"
    assert fresh_job.next_action == {"type": "retry", "message": "boom"}
    db.commit.assert_awaited()
    db.refresh.assert_awaited_with(fresh_job)
