"""ChunkArtifact contract and helpers."""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.section_normalizer import normalize_section_path, section_leaf, serialize_section_path


class ChunkStage(str, Enum):
    RAW = "raw"
    RULE = "rule"
    LLM = "llm"


class ChunkArtifact(BaseModel):
    """Canonical chunk artifact used by indexing and benchmarks."""

    artifact_type: Literal["chunk_artifact"] = "chunk_artifact"
    contract_version: Literal["v1"] = "v1"
    parse_id: str
    paper_id: str
    stage: ChunkStage
    source_chunk_id: str
    chunk_id: str
    parent_source_chunk_id: Optional[str] = None
    content_type: str = "text"
    content_data: str
    section_path: str = ""
    normalized_section_path: str = ""
    section_leaf: str = ""
    page_num: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    anchor_text: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


def build_source_chunk_id(
    *,
    parse_id: str,
    content_type: str,
    page_num: Optional[int],
    section_path: str,
    char_start: Optional[int],
    char_end: Optional[int],
    anchor_text: Optional[str],
) -> str:
    anchor = (anchor_text or "").strip()[:120]
    normalized = serialize_section_path(normalize_section_path(section_path))
    span_part = ""
    if char_start is not None and char_end is not None:
        span_part = f"{char_start}:{char_end}"
    seed = "|".join(
        [
            parse_id,
            str(content_type or "text"),
            str(page_num if page_num is not None else ""),
            normalized,
            span_part,
            anchor,
        ]
    )
    return sha256(seed.encode("utf-8")).hexdigest()


def build_chunk_id(*, source_chunk_id: str, stage: ChunkStage) -> str:
    return f"{source_chunk_id}:{stage.value}"


def build_chunk_artifacts(
    *,
    parse_id: str,
    paper_id: str,
    semantic_chunks: List[Dict[str, Any]],
) -> List[ChunkArtifact]:
    artifacts: List[ChunkArtifact] = []
    seen: set[str] = set()

    for chunk in semantic_chunks:
        content_data = str(chunk.get("text") or "").strip()
        if not content_data:
            continue

        section_path = str(chunk.get("section") or "")
        normalized_tokens = normalize_section_path(section_path)
        normalized = serialize_section_path(normalized_tokens)
        leaf = section_leaf(normalized_tokens)
        page_num = chunk.get("page_start")
        page_num = int(page_num) if page_num is not None else None

        # If semantic chunker did not preserve a real span origin, keep null instead of fake 0/len.
        char_start: Optional[int] = chunk.get("char_start")
        char_end: Optional[int] = chunk.get("char_end")

        anchor_text = chunk.get("anchor_text")
        if not anchor_text:
            anchor_text = content_data[:120]

        source_chunk_id = build_source_chunk_id(
            parse_id=parse_id,
            content_type="text",
            page_num=page_num,
            section_path=section_path,
            char_start=char_start,
            char_end=char_end,
            anchor_text=anchor_text,
        )

        if source_chunk_id in seen:
            raise ValueError(f"Duplicate source_chunk_id generated: {source_chunk_id}")
        seen.add(source_chunk_id)

        warnings: List[str] = []
        if char_start is None or char_end is None:
            warnings.append("missing_char_span")

        artifacts.append(
            ChunkArtifact(
                parse_id=parse_id,
                paper_id=paper_id,
                stage=ChunkStage.RAW,
                source_chunk_id=source_chunk_id,
                chunk_id=build_chunk_id(source_chunk_id=source_chunk_id, stage=ChunkStage.RAW),
                parent_source_chunk_id=None,
                content_type="text",
                content_data=content_data,
                section_path=section_path,
                normalized_section_path=normalized,
                section_leaf=leaf,
                page_num=page_num,
                char_start=char_start,
                char_end=char_end,
                anchor_text=str(anchor_text),
                warnings=warnings,
            )
        )

    return artifacts


def derive_stage_chunk_artifacts(
    base_artifacts: List[ChunkArtifact],
    stage: ChunkStage,
) -> List[ChunkArtifact]:
    if stage == ChunkStage.RAW:
        return list(base_artifacts)

    derived: List[ChunkArtifact] = []
    for artifact in base_artifacts:
        derived.append(
            artifact.model_copy(
                update={
                    "stage": stage,
                    "chunk_id": build_chunk_id(source_chunk_id=artifact.source_chunk_id, stage=stage),
                    "parent_source_chunk_id": artifact.source_chunk_id,
                }
            )
        )
    return derived
