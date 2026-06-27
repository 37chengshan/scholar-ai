from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.tasks.pdf_tasks import process_single_pdf_async


class _FakeSession:
    def __init__(self, existing_task_status: str = "processing") -> None:
        self._existing_task_status = existing_task_status
        self.execute_count = 0
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement, *args, **kwargs):
        self.execute_count += 1
        if self.execute_count == 1:
            return SimpleNamespace(
                first=lambda: SimpleNamespace(
                    id="task-1",
                    status=self._existing_task_status,
                    storage_key="papers/test.pdf",
                )
            )
        return SimpleNamespace()

    async def scalar(self, statement):
        return "cancelled"

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_process_single_pdf_async_stops_when_pipeline_reports_cancelled():
    session = _FakeSession(existing_task_status="processing")
    celery_task = Mock()
    processor = Mock()
    processor.process_pdf_task = AsyncMock(return_value=False)

    with (
        patch("app.tasks.pdf_tasks.AsyncSessionLocal", side_effect=lambda: session),
        patch("app.tasks.pdf_tasks.PDFProcessor", return_value=processor),
        patch("app.tasks.pdf_tasks._sync_import_job_terminal", new=AsyncMock()) as mock_sync_terminal,
    ):
        await process_single_pdf_async("paper-1", celery_task, processing_task_id="task-1")

    processor.process_pdf_task.assert_awaited_once()
    mock_sync_terminal.assert_awaited_once_with(session, "task-1", "cancelled")
    celery_task.update_state.assert_any_call(
        state="REVOKED",
        meta={"paper_id": "paper-1", "status": "cancelled"},
    )


@pytest.mark.asyncio
async def test_process_single_pdf_async_skips_restart_for_already_cancelled_task():
    session = _FakeSession(existing_task_status="cancelled")
    celery_task = Mock()

    with (
        patch("app.tasks.pdf_tasks.AsyncSessionLocal", side_effect=lambda: session),
        patch("app.tasks.pdf_tasks.PDFProcessor") as mock_processor_cls,
        patch("app.tasks.pdf_tasks._sync_import_job_terminal", new=AsyncMock()) as mock_sync_terminal,
    ):
        await process_single_pdf_async("paper-1", celery_task, processing_task_id="task-1")

    mock_processor_cls.return_value.process_pdf_task.assert_not_called()
    mock_sync_terminal.assert_awaited_once_with(session, "task-1", "cancelled")
    celery_task.update_state.assert_called_once_with(
        state="REVOKED",
        meta={"paper_id": "paper-1", "status": "cancelled"},
    )
