from unittest.mock import AsyncMock

import pytest

from app.workers.pipeline_context import PipelineContext
from app.workers.storage_manager import StorageManager


@pytest.mark.asyncio
async def test_store_chunk_rows_dedupes_duplicate_chunk_ids_and_upserts():
    manager = StorageManager.__new__(StorageManager)
    conn = AsyncMock()

    ctx = PipelineContext(
        task_id="task-1",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="storage-key",
    )
    ctx.chunk_results = [
        {
            "chunk_id": "chunk_dup",
            "text": "first copy",
            "section": "intro",
            "page_start": 1,
            "page_end": 1,
            "has_equations": False,
        },
        {
            "chunk_id": "chunk_dup",
            "text": "second copy should be skipped",
            "section": "intro",
            "page_start": 1,
            "page_end": 1,
            "has_equations": False,
        },
        {
            "chunk_id": "chunk_unique",
            "text": "unique row",
            "section": "method",
            "page_start": 2,
            "page_end": 2,
            "has_equations": True,
        },
    ]

    await StorageManager._store_chunk_rows(manager, conn, ctx)

    conn.execute.assert_awaited_once()
    conn.executemany.assert_awaited_once()
    sql, rows = conn.executemany.await_args.args

    assert 'ON CONFLICT (id) DO UPDATE' in sql
    assert len(rows) == 2
    assert [row[0] for row in rows] == ["chunk_dup", "chunk_unique"]
    assert rows[1][7] is True
