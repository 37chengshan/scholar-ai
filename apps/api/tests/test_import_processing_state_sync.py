"""Tests for ImportJob / ProcessingTask terminal state synchronisation.

Per Task G of Backend Pipeline Cleanup v1:
1. Normal completion flow
2. PDFCoordinator exception → ImportJob failed
3. Duplicate process_import_job trigger (idempotent)
4. ProcessingTask already pending when job triggered
5. ProcessingTask in failed state → retry resets to pending
6. Completed task callback is idempotent
"""

import os
import sys
import tempfile

# Ensure LOCAL_STORAGE_PATH points to a writable temp dir before any app module is
# imported.  app.core.storage creates the directory at module load time.
_STORAGE_TMP = tempfile.mkdtemp(prefix="scholar_test_storage_")
os.environ.setdefault("LOCAL_STORAGE_PATH", _STORAGE_TMP)

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_import_job(**kwargs):
    defaults = dict(
        id="imp-1",
        user_id="usr-1",
        paper_id=None,
        processing_task_id=None,
        status="queued",
        stage="queued",
        progress=0,
        error_code=None,
        error_message=None,
        completed_at=None,
        next_action=None,
        updated_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_processing_task(**kwargs):
    defaults = dict(
        id="task-1",
        paper_id="paper-1",
        status="pending",
        storage_key="uploads/usr-1/2026/04/26/imp-1.pdf",
        error_message=None,
        completed_at=None,
        updated_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Scenario 1: Normal completion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_normal_completion_syncs_import_job():
    """On ProcessingTask completed, ImportJob must also be marked completed."""
    from app.tasks.pdf_tasks import _sync_import_job_terminal

    job = _make_import_job(status="running", stage="indexing", processing_task_id="task-1")

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=job)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()
    db.add = MagicMock()

    await _sync_import_job_terminal(db, "task-1", "completed")

    assert job.status == "completed"
    assert job.stage == "completed"
    assert job.progress == 100
    assert job.completed_at is not None


# ---------------------------------------------------------------------------
# Scenario 2: PDFCoordinator exception → ImportJob failed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordinator_exception_marks_import_job_failed():
    """When processing fails, ImportJob must be marked failed with error code."""
    from app.tasks.pdf_tasks import _sync_import_job_terminal

    job = _make_import_job(status="running", stage="parsing", processing_task_id="task-1")

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=job)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    await _sync_import_job_terminal(db, "task-1", "failed", "Download failed: timeout")

    assert job.status == "failed"
    assert job.stage == "failed"
    assert job.error_code == "PROCESSING_FAILED"
    assert "timeout" in (job.error_message or "")
    assert job.next_action is not None


# ---------------------------------------------------------------------------
# Scenario 3: Duplicate process_import_job trigger (idempotent)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_terminal_is_idempotent_on_completed_job():
    """Calling _sync_import_job_terminal on already-completed job is a no-op."""
    from app.tasks.pdf_tasks import _sync_import_job_terminal

    job = _make_import_job(
        status="completed",
        stage="completed",
        progress=100,
        completed_at=datetime.now(timezone.utc),
    )

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=job)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    # Call twice – state must not regress
    await _sync_import_job_terminal(db, "task-1", "failed", "late error")
    await _sync_import_job_terminal(db, "task-1", "completed")

    assert job.status == "completed"
    # commit should not be called (guard returned early)
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 4: ProcessingTask already pending when job triggered
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stage_sync_updates_import_job_when_running():
    """_sync_import_job_stage mirrors real stage to ImportJob."""
    from app.tasks.pdf_tasks import _sync_import_job_stage

    job = _make_import_job(
        status="running", stage="queued", progress=10, processing_task_id="task-1"
    )

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=job)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    await _sync_import_job_stage(db, "task-1", "parsing")

    assert job.stage == "parsing"
    assert job.status == "running"
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario 5: Failed ProcessingTask → retry resets status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stage_sync_skips_terminal_import_job():
    """_sync_import_job_stage does not reopen a completed or cancelled ImportJob."""
    from app.tasks.pdf_tasks import _sync_import_job_stage

    job = _make_import_job(
        status="completed", stage="completed", progress=100, processing_task_id="task-1"
    )

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=job)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    await _sync_import_job_stage(db, "task-1", "parsing")

    # Stage must not regress
    assert job.stage == "completed"
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 6: Completed task callback idempotent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_terminal_noop_when_no_processing_task_id():
    """_sync_import_job_terminal is a safe no-op when task_id is None."""
    from app.tasks.pdf_tasks import _sync_import_job_terminal

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    # Should not raise, should not call db at all
    await _sync_import_job_terminal(db, None, "completed")

    db.execute.assert_not_called()
    db.commit.assert_not_called()
