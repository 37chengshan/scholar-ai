from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.workers.pipeline_context import PipelineContext
from app.workers.storage_manager import StorageManager


def test_embedding_batch_size_for_device_uses_runtime_specific_defaults():
    with patch("app.workers.storage_manager.settings") as mock_settings:
        mock_settings.EMBEDDING_BATCH_SIZE_CPU = 16
        mock_settings.EMBEDDING_BATCH_SIZE_MPS = 8
        mock_settings.EMBEDDING_BATCH_SIZE_CUDA = 32

        assert StorageManager._embedding_batch_size_for_device("cpu") == 16
        assert StorageManager._embedding_batch_size_for_device("mps") == 8
        assert StorageManager._embedding_batch_size_for_device("cuda") == 32
        assert StorageManager._embedding_batch_size_for_device("unknown") == 16


def test_should_empty_mps_cache_only_when_interval_enabled():
    with patch("app.workers.storage_manager.settings") as mock_settings:
        mock_settings.EMBEDDING_MPS_EMPTY_CACHE_INTERVAL = 0
        assert StorageManager._should_empty_mps_cache("mps", 1) is False

        mock_settings.EMBEDDING_MPS_EMPTY_CACHE_INTERVAL = 3
        assert StorageManager._should_empty_mps_cache("cpu", 3) is False
        assert StorageManager._should_empty_mps_cache("mps", 2) is False
        assert StorageManager._should_empty_mps_cache("mps", 3) is True


@pytest.mark.asyncio
async def test_store_vectors_uses_device_batch_size_without_forced_mps_cache_clear():
    manager = StorageManager.__new__(StorageManager)
    manager.MIN_CHUNK_QUALITY = 0.0
    manager.parser = Mock()
    manager.parser.chunk_by_semantic.return_value = [
        {"text": "chunk 1", "page_start": 1, "section": "intro", "char_start": 0, "char_end": 7},
        {"text": "chunk 2", "page_start": 1, "section": "intro", "char_start": 8, "char_end": 15},
        {"text": "chunk 3", "page_start": 2, "section": "method", "char_start": 0, "char_end": 7},
    ]
    manager.qwen3vl_service = SimpleNamespace(
        is_loaded=lambda: True,
        load_model=lambda: None,
        get_device=lambda: "cpu",
        encode_text=Mock(side_effect=lambda batch: [[0.0] * 2048 for _ in batch]),
    )
    manager.milvus = Mock()
    manager.milvus.delete_all_vectors_by_paper = Mock()
    manager.milvus.insert_contents_batched = Mock(return_value=["c1", "c2", "c3"])
    manager._store_summary_index = AsyncMock()

    ctx = PipelineContext(
        task_id="task-1",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="storage-key",
    )
    ctx.parse_result = {
        "items": [{"type": "text", "text": "abc", "page": 1}],
        "metadata": {},
    }
    ctx.metadata = {"title": "Test"}
    ctx.image_results = []
    ctx.table_results = []
    ctx.imrad = None

    with patch("app.workers.storage_manager.settings") as mock_settings, patch(
        "app.workers.storage_manager.enrich_chunk",
        side_effect=lambda **kwargs: {"content_data": kwargs["chunk"]["text"], "context_window": ""},
    ), patch("app.workers.storage_manager.calculate_chunk_quality", return_value=1.0), patch(
        "app.workers.storage_manager.torch.mps.empty_cache"
    ) as mock_empty_cache:
        mock_settings.EMBEDDING_BATCH_SIZE_CPU = 2
        mock_settings.EMBEDDING_BATCH_SIZE_MPS = 8
        mock_settings.EMBEDDING_BATCH_SIZE_CUDA = 32
        mock_settings.EMBEDDING_MPS_EMPTY_CACHE_INTERVAL = 0

        chunk_ids = await StorageManager._store_vectors(manager, ctx)

    assert chunk_ids == ["c1", "c2", "c3"]
    manager.milvus.delete_all_vectors_by_paper.assert_called_once_with("paper-1")
    assert manager.qwen3vl_service.encode_text.call_count == 2
    assert len(manager.qwen3vl_service.encode_text.call_args_list[0].args[0]) == 2
    assert len(manager.qwen3vl_service.encode_text.call_args_list[1].args[0]) == 1
    assert len({record["chunk_id"] for record in ctx.chunk_results}) == 3
    assert [record["page_num"] for record in ctx.chunk_results] == [1, 1, 2]
    assert [record["char_start"] for record in ctx.chunk_results] == [0, 8, 0]
    mock_empty_cache.assert_not_called()


@pytest.mark.asyncio
async def test_store_summary_index_uses_canonical_source_chunk_id():
    manager = StorageManager.__new__(StorageManager)
    manager.qwen3vl_service = SimpleNamespace(
        encode_text=Mock(return_value=[[0.1, 0.2], [0.3, 0.4]]),
    )
    manager.milvus = Mock()
    manager.milvus.delete_all_vectors_by_paper = Mock()
    manager.milvus.insert_summaries_batched = Mock(return_value=[1, 2])
    manager._truncate_summary_text = lambda text: text

    ctx = PipelineContext(
        task_id="task-1",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="storage-key",
    )
    ctx.metadata = {"title": "Test"}

    text_contents = [
        {
            "text": "A" * 120,
            "section": "intro",
            "chunk_id": "milvus-auto-id-1",
            "source_chunk_id": "chunk_canonical_intro",
        },
        {
            "text": "B" * 120,
            "section": "intro",
            "chunk_id": "milvus-auto-id-2",
            "source_chunk_id": "chunk_canonical_intro_2",
        },
    ]

    await StorageManager._store_summary_index(manager, ctx, text_contents)

    inserted_entries = manager.milvus.insert_summaries_batched.call_args.args[0]
    assert inserted_entries[0]["source_chunk_id"] == "chunk_canonical_intro"
    assert inserted_entries[1]["source_chunk_id"] == "chunk_canonical_intro"
