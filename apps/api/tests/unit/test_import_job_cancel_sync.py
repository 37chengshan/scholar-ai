from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.imports.jobs import cancel_import_job


@pytest.mark.asyncio
async def test_cancel_import_job_cascades_to_processing_task():
    job = SimpleNamespace(
        id="job-1",
        status="running",
        cancelled_at=None,
        processing_task_id="task-1",
    )
    fake_db = object()

    service = SimpleNamespace(
        get_job=AsyncMock(return_value=job),
        set_cancelled=AsyncMock(
            side_effect=lambda current_job, _db: _set_cancelled(current_job)
        ),
        add_event=AsyncMock(return_value=None),
    )

    with (
        patch("app.api.imports.jobs.ImportJobService", return_value=service),
        patch("app.api.imports.jobs.TaskService.cancel_task", new=AsyncMock()) as mock_cancel_task,
    ):
        response = await cancel_import_job("job-1", user_id="user-1", db=fake_db)

    mock_cancel_task.assert_awaited_once_with(fake_db, "task-1", "user-1")
    service.set_cancelled.assert_awaited_once()
    assert response.data["status"] == "cancelled"


def _set_cancelled(job):
    job.status = "cancelled"
    job.cancelled_at = datetime.now(timezone.utc)
    return job
