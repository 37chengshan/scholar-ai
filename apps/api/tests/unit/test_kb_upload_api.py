"""Unit tests for KB-native upload endpoint."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.api.kb.kb_import import upload_pdf_to_kb
from app.models.knowledge_base import KnowledgeBase


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_upload_pdf_to_kb_creates_kb_bound_paper():
    db = AsyncMock()
    db.add = MagicMock()
    kb = KnowledgeBase(
        id="kb-123",
        user_id="user-123",
        name="Test KB",
        description="",
        category="其他",
        embedding_model="bge-m3",
        parse_engine="docling",
        chunk_strategy="by-paragraph",
        enable_graph=False,
        enable_imrad=True,
        enable_chart_understanding=False,
        enable_multimodal_search=False,
        enable_comparison=False,
        paper_count=0,
        chunk_count=0,
        entity_count=0,
    )

    db.execute.side_effect = [
        _ScalarResult(kb),  # KB lookup
        _ScalarResult(None),  # duplicate paper lookup
    ]

    file = UploadFile(filename="paper.pdf", file=BytesIO(b"%PDF-1.4\nhello\n%%EOF"))

    mock_open = MagicMock()
    mock_open.__aenter__.return_value.write = AsyncMock()
    mock_open.__aexit__.return_value = False

    with (
        patch("app.api.kb.kb_import.os.makedirs"),
        patch("app.api.kb.kb_import.aiofiles.open", return_value=mock_open),
        patch("app.api.kb.kb_import.process_single_pdf_task.delay") as mock_delay,
    ):
        response = await upload_pdf_to_kb(
            "kb-123",
            file=file,
            user_id="user-123",
            db=db,
        )

    added_paper = db.add.call_args_list[0].args[0]
    added_task = db.add.call_args_list[1].args[0]
    added_upload_history = db.add.call_args_list[2].args[0]

    assert added_paper.knowledge_base_id == "kb-123"
    assert added_paper.user_id == "user-123"
    assert added_task.paper_id == added_paper.id
    assert added_upload_history.paper_id == added_paper.id
    assert added_upload_history.filename == "paper.pdf"
    assert kb.paper_count == 1
    mock_delay.assert_called_once_with(added_paper.id)
    assert response.data["kbId"] == "kb-123"
    assert response.data["paperId"] == added_paper.id
    assert response.data["taskId"] == added_task.id
