"""PR7 regression tests for evidence metadata and quality gate behavior."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.workers.pipeline_context import PipelineContext
from app.workers.storage_manager import StorageManager


def test_build_evidence_metadata_extracts_references_and_span():
    chunk = {
        "paper_id": "paper-1",
        "section": "results",
        "raw_section_path": "Findings",
        "normalized_section_path": "result",
        "normalized_section_leaf": "result",
        "section_level": 1,
        "parent_section_path": "",
        "page_start": 5,
        "char_start": 10,
        "char_end": 90,
        "anchor_text": "Figure 2 reports results",
        "chunk_id": "chunk_abc123",
    }
    text = "Figure 2: Model architecture. Table 3 reports metrics for ablation."
    parse_metadata = {
        "parse_mode": "native",
        "ocr_used": False,
        "parse_warnings": [],
        "chunk_strategy": {"mode": "section_adaptive"},
    }

    metadata = StorageManager._build_evidence_metadata(chunk, text, parse_metadata)

    assert metadata["evidence_version"] == "v1"
    assert metadata["section_path"] == "results"
    assert metadata["raw_section_path"] == "Findings"
    assert metadata["normalized_section_path"] == "result"
    assert metadata["normalized_section_leaf"] == "result"
    assert metadata["section_level"] == 1
    assert metadata["parent_section_path"] == ""
    assert metadata["chunk_id"] == "chunk_abc123"
    assert metadata["char_start"] == 10
    assert metadata["char_end"] == 90
    assert metadata["anchor_text"] == "Figure 2 reports results"
    assert metadata["page_num"] == 5
    assert metadata["figure_id"] == "figure-2"
    assert metadata["table_id"] == "table-3"
    assert metadata["caption"] == "Model architecture"
    assert metadata["source_span"]["start_char"] == 0
    assert metadata["source_span"]["end_char"] <= 200


@pytest.mark.asyncio
async def test_store_vectors_backfills_quality_gate_even_when_nothing_indexed():
    manager = StorageManager.__new__(StorageManager)
    manager.MIN_CHUNK_QUALITY = 0.25
    manager.parser = Mock()
    manager.parser.chunk_by_semantic.return_value = [
        {
            "text": "tiny low quality chunk",
            "page_start": 1,
            "section": "methods",
            "has_equations": False,
            "has_figures": False,
        }
    ]

    manager.qwen3vl_service = SimpleNamespace(
        is_loaded=lambda: True,
        load_model=lambda: None,
        get_device=lambda: "cpu",
        encode_text=lambda batch: [[0.0] * 2048 for _ in batch],
    )
    manager.milvus = Mock()
    manager.milvus.insert_contents_batched = Mock(return_value=[])

    ctx = PipelineContext(
        task_id="task-1",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="k",
    )
    ctx.parse_result = {
        "items": [{"type": "text", "text": "abc", "page": 1}],
        "metadata": {},
    }
    ctx.image_results = []
    ctx.table_results = []
    ctx.imrad = None

    with patch("app.workers.storage_manager.calculate_chunk_quality", return_value=0.1):
        chunk_ids = await StorageManager._store_vectors(manager, ctx)

    assert chunk_ids == []
    assert ctx.parse_result["metadata"]["quality_gate"]["input_chunks"] == 1
    assert ctx.parse_result["metadata"]["quality_gate"]["indexed_chunks"] == 0
    assert ctx.parse_result["metadata"]["quality_gate"]["skipped_chunks"] == 1
    manager.milvus.insert_contents_batched.assert_not_called()


@pytest.mark.asyncio
async def test_store_vectors_handles_missing_parse_items_gracefully():
    manager = StorageManager.__new__(StorageManager)
    manager.MIN_CHUNK_QUALITY = 0.25
    manager.parser = Mock()
    manager.qwen3vl_service = SimpleNamespace(
        is_loaded=lambda: True,
        load_model=lambda: None,
        get_device=lambda: "cpu",
        encode_text=lambda batch: [[0.0] * 2048 for _ in batch],
    )
    manager.milvus = Mock()
    manager.milvus.insert_contents_batched = Mock(return_value=[])

    ctx = PipelineContext(
        task_id="task-missing-items",
        paper_id="paper-1",
        user_id="user-1",
        storage_key="k",
    )
    ctx.parse_result = {"metadata": {}}
    ctx.image_results = []
    ctx.table_results = []
    ctx.imrad = None

    chunk_ids = await StorageManager._store_vectors(manager, ctx)

    assert chunk_ids == []
    assert ctx.parse_result["metadata"]["quality_gate"]["skip_reason"] == "missing_parse_items"
    manager.milvus.insert_contents_batched.assert_not_called()
