"""Regression tests for chunk identity field isolation and stage alignment."""

from app.workers.storage_manager import StorageManager


def test_text_record_uses_current_chunk_fields_without_leakage() -> None:
    chunk_a = {
        "chunk_id": "chunk-a",
        "source_chunk_id": "source-a",
        "stage": "raw",
        "parent_source_chunk_id": None,
        "page_num": 1,
        "char_start": 10,
        "char_end": 30,
        "anchor_text": "anchor-a",
        "section_path": "Intro",
        "normalized_section_path": "intro",
        "section_leaf": "intro",
    }
    chunk_b = {
        "chunk_id": "chunk-b",
        "source_chunk_id": "source-b",
        "stage": "raw",
        "parent_source_chunk_id": None,
        "page_num": 5,
        "char_start": 50,
        "char_end": 80,
        "anchor_text": "anchor-b",
        "section_path": "Methods",
        "normalized_section_path": "methods",
        "section_leaf": "methods",
    }

    record_a = StorageManager._build_text_record_from_chunk_artifact(
        chunk_artifact=chunk_a,
        paper_id="v2-p-001",
        user_id="u1",
        chunk_text="ctx-a",
        raw_text="raw-a",
        embedding=[0.1, 0.2],
        section="intro",
        raw_data={},
    )
    record_b = StorageManager._build_text_record_from_chunk_artifact(
        chunk_artifact=chunk_b,
        paper_id="v2-p-001",
        user_id="u1",
        chunk_text="ctx-b",
        raw_text="raw-b",
        embedding=[0.3, 0.4],
        section="methods",
        raw_data={},
    )

    assert record_a["chunk_id"] == "chunk-a"
    assert record_a["source_chunk_id"] == "source-a"
    assert record_a["page_num"] == 1
    assert record_a["char_start"] == 10
    assert record_a["char_end"] == 30

    assert record_b["chunk_id"] == "chunk-b"
    assert record_b["source_chunk_id"] == "source-b"
    assert record_b["page_num"] == 5
    assert record_b["char_start"] == 50
    assert record_b["char_end"] == 80
