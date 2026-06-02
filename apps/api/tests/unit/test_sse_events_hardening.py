"""Unit tests for SSE events hardening (Phase 5.0-3 T1).

Covers:
- Error message sanitization (no internal exception leakage)
- Terminal event handling (completed, failed, cancelled)
- Stage change and progress event emission
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.imports.events import stream_import_progress


class _MockJob:
    """Minimal ImportJob mock for SSE stream tests."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "imp_test123")
        self.user_id = kwargs.get("user_id", "user-1")
        self.status = kwargs.get("status", "running")
        self.stage = kwargs.get("stage", "parsing")
        self.progress = kwargs.get("progress", 50)
        self.next_action = kwargs.get("next_action", None)
        self.error_code = kwargs.get("error_code", None)
        self.error_message = kwargs.get("error_message", None)
        self.paper_id = kwargs.get("paper_id", None)


def _parse_sse_text(text):
    """Parse raw SSE text into list of (event_type, data_dict) tuples."""
    events = []
    for block in text.strip().split("\n\n"):
        event_type = None
        data_str = None
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
        if event_type and data_str:
            events.append((event_type, json.loads(data_str)))
    return events


async def _collect_stream(response):
    """Collect all chunks from a StreamingResponse."""
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return "".join(chunks)


@pytest.mark.asyncio
async def test_sse_error_does_not_leak_internal_exception():
    """Verify that SSE error events return a generic message, not str(e)."""
    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(
        side_effect=RuntimeError("DB connection pool exhausted")
    )

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_test", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    error_events = [(t, d) for t, d in events if t == "error"]
    assert len(error_events) >= 1
    assert error_events[0][1]["message"] == "Internal stream error"
    assert "DB connection pool exhausted" not in json.dumps(error_events[0][1])


@pytest.mark.asyncio
async def test_sse_completed_event_includes_paper_id():
    """Verify that completed terminal event includes paperId."""
    mock_job = _MockJob(
        status="completed",
        stage="completed",
        progress=100,
        paper_id="paper-abc123",
    )

    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(return_value=mock_job)

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_test", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    completed_events = [(t, d) for t, d in events if t == "completed"]
    assert len(completed_events) >= 1

    data = completed_events[0][1]
    assert data["paperId"] == "paper-abc123"
    assert data["importJobId"] == "imp_test123"


@pytest.mark.asyncio
async def test_sse_failed_event_sends_job_error_details():
    """Verify that failed status sends error event with job error fields."""
    mock_job = _MockJob(
        status="failed",
        stage="parsing",
        progress=30,
        error_code="PDF_PARSE_FAILED",
        error_message="Invalid PDF structure",
    )

    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(return_value=mock_job)

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_test", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    error_events = [(t, d) for t, d in events if t == "error"]
    assert len(error_events) >= 1

    data = error_events[0][1]
    assert data["code"] == "PDF_PARSE_FAILED"
    assert data["message"] == "Invalid PDF structure"


@pytest.mark.asyncio
async def test_sse_cancelled_event():
    """Verify that cancelled status sends cancelled terminal event."""
    mock_job = _MockJob(status="cancelled", stage="parsing", progress=20)

    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(return_value=mock_job)

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_test", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    cancelled_events = [(t, d) for t, d in events if t == "cancelled"]
    assert len(cancelled_events) >= 1


@pytest.mark.asyncio
async def test_sse_job_not_found():
    """Verify that missing job sends error event with 'Job not found'."""
    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(return_value=None)

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_missing", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    error_events = [(t, d) for t, d in events if t == "error"]
    assert len(error_events) >= 1
    assert error_events[0][1]["message"] == "Job not found"


@pytest.mark.asyncio
async def test_sse_stage_change_and_progress_events():
    """Verify that stage_change and progress events are emitted for running jobs."""
    # Use a two-iteration approach: first call returns running, second returns completed
    mock_job_running = _MockJob(status="running", stage="embedding", progress=75)
    mock_job_completed = _MockJob(
        status="completed", stage="completed", progress=100, paper_id="paper-done"
    )

    mock_service = MagicMock()
    mock_service.get_job = AsyncMock(
        side_effect=[mock_job_running, mock_job_completed]
    )

    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.imports.events.ImportJobService", return_value=mock_service),
        patch("app.api.imports.events.AsyncSessionLocal", return_value=mock_session_cm),
    ):
        response = await stream_import_progress(job_id="imp_test", user_id="user-1")
        text = await _collect_stream(response)

    events = _parse_sse_text(text)
    event_types = [t for t, _ in events]

    assert "stage_change" in event_types
    assert "progress" in event_types
    assert "status_update" in event_types
    assert "completed" in event_types
