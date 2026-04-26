#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "papers"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_4"

OFFICIAL_PROVIDER = "tongyi"
OFFICIAL_MODEL = "tongyi-embedding-vision-flash-2026-03-06"

STAGES = ["raw", "rule", "llm"]

REQUIRED_CHUNK_FIELDS = [
    "source_chunk_id",
    "chunk_id",
    "paper_id",
    "parse_id",
    "page_num",
    "section_path",
    "normalized_section_path",
    "content_type",
    "content_data",
    "anchor_text",
    "char_start",
    "char_end",
    "stage",
    "indexable",
]

REQUIRED_SCHEMA_FIELDS = [
    "source_chunk_id",
    "chunk_id",
    "paper_id",
    "user_id",
    "parse_id",
    "page_num",
    "content_type",
    "section",
    "normalized_section_path",
    "anchor_text",
    "char_start",
    "char_end",
    "stage",
    "indexable",
    "embedding_status",
    "content_data",
    "embedding",
]

OFFICIAL_OUTPUT_FIELDS = [
    "source_chunk_id",
    "paper_id",
    "page_num",
    "content_type",
    "section",
    "anchor_text",
    "content_data",
]


@dataclass(frozen=True)
class PaperArtifacts:
    paper_id: str
    parse_artifact_path: Path
    chunks_raw_path: Path
    chunks_rule_path: Path
    chunks_llm_path: Path


def stage_collection_name(stage: str, suffix: str) -> str:
    return f"paper_contents_v2_api_tongyi_flash_{stage}_{suffix}"


def deprecated_collection_prefixes() -> Tuple[str, ...]:
    return (
        "paper_contents_v2_qwen_v2_",
        "paper_contents_v2_specter2_",
        "paper_contents_v2_bge_",
        "paper_contents_v2_api_tongyi_flash_raw_v2_3",
        "paper_contents_v2_api_tongyi_flash_rule_v2_3",
        "paper_contents_v2_api_tongyi_flash_llm_v2_3",
    )


def is_deprecated_output_collection(name: str) -> bool:
    if name == "paper_contents":
        return True
    for prefix in deprecated_collection_prefixes():
        if prefix.endswith("_") and name.startswith(prefix):
            return True
        if name == prefix:
            return True
    return False


def collect_paper_artifacts(artifact_root: Path, limit_papers: Optional[int] = None) -> List[PaperArtifacts]:
    if not artifact_root.exists():
        return []

    papers: List[PaperArtifacts] = []
    for paper_dir in sorted([p for p in artifact_root.iterdir() if p.is_dir()]):
        paper_id = paper_dir.name
        papers.append(
            PaperArtifacts(
                paper_id=paper_id,
                parse_artifact_path=paper_dir / "parse_artifact.json",
                chunks_raw_path=paper_dir / "chunks_raw.json",
                chunks_rule_path=paper_dir / "chunks_rule.json",
                chunks_llm_path=paper_dir / "chunks_llm.json",
            )
        )
        if limit_papers is not None and len(papers) >= limit_papers:
            break
    return papers


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, title: str, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [f"# {title}", ""] + lines
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def chunk_file_for_stage(artifacts: PaperArtifacts, stage: str) -> Path:
    if stage == "raw":
        return artifacts.chunks_raw_path
    if stage == "rule":
        return artifacts.chunks_rule_path
    if stage == "llm":
        return artifacts.chunks_llm_path
    raise ValueError(f"unsupported stage: {stage}")


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def required_field_missing(record: Dict[str, Any], fields: Iterable[str]) -> List[str]:
    missing: List[str] = []
    for key in fields:
        if key not in record:
            missing.append(key)
            continue
        if record[key] is None:
            missing.append(key)
            continue
        if isinstance(record[key], str) and not record[key].strip() and key not in {"anchor_text"}:
            missing.append(key)
    return missing


def content_type_valid(content_type: Any) -> bool:
    return str(content_type or "") in {"text", "table", "figure", "caption", "page"}


def ensure_query_dim_matches_collection_dim(query_dim: int, collection_dim: int) -> None:
    if int(query_dim) != int(collection_dim):
        raise RuntimeError(
            f"query_dim != collection_dim ({query_dim} != {collection_dim})"
        )


def source_chunk_set(chunks: List[Dict[str, Any]]) -> Set[str]:
    return {str(c.get("source_chunk_id") or "") for c in chunks if str(c.get("source_chunk_id") or "")}


def unique_source_chunk_ids(chunks: List[Dict[str, Any]]) -> bool:
    seen: Set[str] = set()
    for chunk in chunks:
        sid = str(chunk.get("source_chunk_id") or "")
        if not sid:
            continue
        if sid in seen:
            return False
        seen.add(sid)
    return True


def infer_ingest_status(errors: List[str]) -> str:
    return "PASS" if not errors else "BLOCKED"
