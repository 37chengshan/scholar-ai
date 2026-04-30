"""Regression tests for StorageManager title overwrite rules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.pipeline_context import PipelineContext
from app.workers.storage_manager import StorageManager


@pytest.fixture
def storage_manager():
    with (
        patch("app.workers.storage_manager.Neo4jService", return_value=MagicMock()),
        patch("app.workers.storage_manager.NotesGenerator", return_value=MagicMock()),
        patch("app.workers.storage_manager.DoclingParser", return_value=MagicMock()),
        patch("app.workers.storage_manager.get_qwen3vl_service", return_value=MagicMock()),
    ):
        return StorageManager(MagicMock())


def make_ctx(title: str | None) -> PipelineContext:
    ctx = PipelineContext(
        task_id="task-1",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="storage-key",
    )
    ctx.metadata = {"title": title, "authors": ["Author A"]}
    ctx.imrad = {}
    ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}
    return ctx


@pytest.mark.asyncio
async def test_store_paper_metadata_preserves_trusted_import_title(storage_manager: StorageManager):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value="Attention Is All You Need")

    ctx = make_ctx("Provided proper attribution is provided, Google hereby grants permission to")

    await storage_manager._store_paper_metadata(conn, ctx)

    call_args = conn.execute.call_args[0]
    sql = call_args[0]
    stored_title = call_args[4]
    assert "title = COALESCE($4::text, title)" in sql
    assert stored_title is None


@pytest.mark.asyncio
async def test_store_paper_metadata_replaces_filename_placeholder(storage_manager: StorageManager):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=["attention-is-all-you-need.pdf", None])

    ctx = make_ctx("Attention Is All You Need")

    await storage_manager._store_paper_metadata(conn, ctx)

    call_args = conn.execute.call_args[0]
    sql = call_args[0]
    stored_title = call_args[4]
    assert "title = COALESCE($4::text, title)" in sql
    assert stored_title == "Attention Is All You Need"
