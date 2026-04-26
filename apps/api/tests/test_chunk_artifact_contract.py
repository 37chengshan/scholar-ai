"""Tests for ChunkArtifact contract."""

from app.contracts.chunk_artifact import (
    ChunkStage,
    build_chunk_artifacts,
    derive_stage_chunk_artifacts,
)


def test_chunk_artifacts_keep_stable_source_ids_across_stages() -> None:
    semantic_chunks = [
        {
            "text": "Introduction content",
            "section": "Introduction",
            "page_start": 1,
            "anchor_text": "Introduction content",
        },
        {
            "text": "Method content",
            "section": "Methods",
            "page_start": 2,
            "anchor_text": "Method content",
        },
    ]

    raw = build_chunk_artifacts(
        parse_id="parse-abc",
        paper_id="v2-p-001",
        semantic_chunks=semantic_chunks,
    )
    rule = derive_stage_chunk_artifacts(raw, ChunkStage.RULE)
    llm = derive_stage_chunk_artifacts(raw, ChunkStage.LLM)

    assert len(raw) == 2
    assert {c.source_chunk_id for c in raw} == {c.source_chunk_id for c in rule}
    assert {c.source_chunk_id for c in raw} == {c.source_chunk_id for c in llm}

    for c in raw:
        assert c.stage == ChunkStage.RAW
        assert c.parent_source_chunk_id is None

    for c in rule + llm:
        assert c.parent_source_chunk_id == c.source_chunk_id
        assert c.chunk_id.endswith(f":{c.stage.value}")


def test_chunk_artifacts_mark_missing_char_span_warning() -> None:
    semantic_chunks = [{"text": "No span", "section": "Results", "page_start": 3}]
    raw = build_chunk_artifacts(
        parse_id="parse-xyz",
        paper_id="v2-p-003",
        semantic_chunks=semantic_chunks,
    )

    assert raw[0].char_start is None
    assert raw[0].char_end is None
    assert "missing_char_span" in raw[0].warnings
