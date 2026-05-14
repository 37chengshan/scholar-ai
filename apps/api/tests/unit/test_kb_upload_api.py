"""Unit tests for KB-native upload endpoint."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.api.kb.kb_import import upload_pdf_to_kb


@pytest.mark.asyncio
async def test_upload_pdf_to_kb_queues_import_job():
    db = AsyncMock()
    file = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.4\nhello\n%%EOF"))

    job = SimpleNamespace(id="imp_123", status="created", stage="awaiting_input", progress=0)
    mock_open = MagicMock()
    mock_open.__aenter__.return_value.write = AsyncMock()
    mock_open.__aexit__.return_value = False

    with (
        patch("app.api.kb.kb_import._get_kb_or_404", new=AsyncMock(return_value=MagicMock())),
        patch("app.api.kb.kb_import.ImportJobService") as mock_service_cls,
        patch("app.api.kb.kb_import.os.makedirs"),
        patch("app.api.kb.kb_import.aiofiles.open", return_value=mock_open),
        patch("app.api.kb.kb_import.process_import_job.delay") as mock_delay,
    ):
        mock_service = MagicMock()
        mock_service.create_job = AsyncMock(return_value=job)
        mock_service.set_file_info = AsyncMock()
        mock_service_cls.return_value = mock_service

        response = await upload_pdf_to_kb(
            "kb-123",
            file=file,
            user_id="user-123",
            db=db,
        )

    mock_service.create_job.assert_awaited_once()
    mock_service.set_file_info.assert_awaited_once()
    mock_delay.assert_called_once_with("imp_123")
    assert response.success is True
    assert response.data["kbId"] == "kb-123"
    assert response.data["importJobId"] == "imp_123"
    assert response.data["paperId"] is None
    assert response.data["taskId"] == "imp_123"
    assert response.data["status"] == "queued"
    assert response.data["stage"] == "uploaded"
    assert response.data["progress"] == 10
