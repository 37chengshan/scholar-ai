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
        {"text": "chunk 1", "page_start": 1, "section": "intro"},
        {"text": "chunk 2", "page_start": 1, "section": "intro"},
        {"text": "chunk 3", "page_start": 2, "section": "method"},
    ]
    manager.qwen3vl_service = SimpleNamespace(
        is_loaded=lambda: True,
        load_model=lambda: None,
        get_device=lambda: "cpu",
        encode_text=Mock(side_effect=lambda batch: [[0.0] * 2048 for _ in batch]),
    )
    manager.milvus = Mock()
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
    assert manager.qwen3vl_service.encode_text.call_count == 2
    assert len(manager.qwen3vl_service.encode_text.call_args_list[0].args[0]) == 2
    assert len(manager.qwen3vl_service.encode_text.call_args_list[1].args[0]) == 1
    mock_empty_cache.assert_not_called()
