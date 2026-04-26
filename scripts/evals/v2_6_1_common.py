#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pymilvus import Collection, connections


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.model_gateway import create_embedding_provider
from scripts.evals.v2_4_common import read_json, stage_collection_name, write_json, write_markdown
from scripts.evals.v2_6_official_rag_evaluation import load_golden_rows, select_regression_rows


OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_6_1"
DEFAULT_GOLDEN_PATH = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "papers"


@dataclass(frozen=True)
class RegressionRow:
    query_id: str
    query: str
    query_family: str
    expected_paper_ids: List[str]
    expected_source_chunk_ids: List[str]
    expected_content_types: List[str]
    expected_sections: List[str]


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def load_regression_rows(golden_path: Path = DEFAULT_GOLDEN_PATH, max_queries: int = 16) -> List[RegressionRow]:
    rows = load_golden_rows(golden_path, mode="official")
    selected = select_regression_rows(rows, max_queries=max_queries)
    return [
        RegressionRow(
            query_id=row.query_id,
            query=row.query,
            query_family=row.query_family,
            expected_paper_ids=list(row.expected_paper_ids),
            expected_source_chunk_ids=list(row.expected_source_chunk_ids),
            expected_content_types=list(row.expected_content_types),
            expected_sections=list(row.expected_sections),
        )
        for row in selected
    ]


def stage_collection(stage: str, suffix: str) -> str:
    return stage_collection_name(stage, suffix)


def connect_milvus(alias: str, host: str, port: int) -> None:
    connections.connect(alias=alias, host=host, port=port)


def collection_dim(collection: Collection, vector_field: str = "embedding") -> int:
    for field in getattr(collection.schema, "fields", []):
        if getattr(field, "name", "") == vector_field:
            params = getattr(field, "params", {}) or {}
            if isinstance(params, dict) and params.get("dim") is not None:
                return int(params.get("dim"))
    return 0


def query_all_rows(collection: Collection, output_fields: Sequence[str], limit: int = 20000) -> List[Dict[str, Any]]:
    return list(collection.query(expr="id >= 0", output_fields=list(output_fields), limit=limit))


def load_stage_collection_rows(
    *,
    alias: str,
    collection_suffix: str,
    stage: str,
    output_fields: Sequence[str],
    limit: int = 20000,
) -> Tuple[str, Collection, List[Dict[str, Any]]]:
    name = stage_collection(stage, collection_suffix)
    col = Collection(name, using=alias)
    col.load()
    rows = query_all_rows(col, output_fields=output_fields, limit=limit)
    return name, col, rows


def _chunk_file_for_stage(paper_dir: Path, stage: str) -> Path:
    if stage == "raw":
        return paper_dir / "chunks_raw.json"
    if stage == "rule":
        return paper_dir / "chunks_rule.json"
    if stage == "llm":
        return paper_dir / "chunks_llm.json"
    raise ValueError(f"unsupported stage: {stage}")


def load_artifact_rows_by_stage(artifact_root: Path = DEFAULT_ARTIFACT_ROOT) -> Dict[str, List[Dict[str, Any]]]:
    by_stage: Dict[str, List[Dict[str, Any]]] = {"raw": [], "rule": [], "llm": []}
    for paper_dir in sorted([p for p in artifact_root.iterdir() if p.is_dir()]):
        for stage in ["raw", "rule", "llm"]:
            path = _chunk_file_for_stage(paper_dir, stage)
            if not path.exists():
                continue
            payload = read_json(path)
            if isinstance(payload, list):
                by_stage[stage].extend(payload)
    return by_stage


def index_by_source_chunk_id(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("source_chunk_id") or "").strip()
        if sid and sid not in out:
            out[sid] = row
    return out


def source_set(rows: Iterable[Dict[str, Any]]) -> Set[str]:
    return {
        str(row.get("source_chunk_id") or "").strip()
        for row in rows
        if str(row.get("source_chunk_id") or "").strip()
    }


def deduce_source_id(hit: Any) -> Tuple[str, str]:
    entity = getattr(hit, "entity", None)
    if entity is not None:
        sid = str(entity.get("source_chunk_id") or "").strip()
        if sid:
            return sid, "entity.source_chunk_id"
        raw_data = entity.get("raw_data") or {}
        if isinstance(raw_data, dict):
            sid2 = str(raw_data.get("source_chunk_id") or "").strip()
            if sid2:
                return sid2, "raw_data.source_chunk_id"
    hit_id = str(getattr(hit, "id", "") or "").strip()
    if hit_id:
        return hit_id, "id"
    return "", "unknown"


def run_dense_search(
    *,
    collection: Collection,
    query_vector: List[float],
    top_k: int,
    expr: Optional[str],
    output_fields: Sequence[str],
) -> List[Dict[str, Any]]:
    kwargs: Dict[str, Any] = {
        "data": [query_vector],
        "anns_field": "embedding",
        "param": {"metric_type": "COSINE", "params": {"nprobe": 10}},
        "limit": top_k,
        "output_fields": list(output_fields),
    }
    if expr:
        kwargs["expr"] = expr
    raw = collection.search(**kwargs)

    hits: List[Dict[str, Any]] = []
    for batch in raw:
        for hit in batch:
            sid, source_from = deduce_source_id(hit)
            entity = getattr(hit, "entity", None)
            paper_id = str(entity.get("paper_id") or "") if entity is not None else ""
            section = str(entity.get("section") or "") if entity is not None else ""
            content_type = str(entity.get("content_type") or "") if entity is not None else ""
            anchor_text = str(entity.get("anchor_text") or "") if entity is not None else ""
            hits.append(
                {
                    "milvus_id": str(getattr(hit, "id", "") or ""),
                    "source_chunk_id": sid,
                    "source_chunk_id_field_source": source_from,
                    "paper_id": paper_id,
                    "section": section,
                    "content_type": content_type,
                    "anchor_text": anchor_text,
                    "distance": float(getattr(hit, "distance", 0.0) or 0.0),
                }
            )
    return hits


def mean(values: Iterable[float]) -> float:
    seq = [float(v) for v in values]
    if not seq:
        return 0.0
    return sum(seq) / float(len(seq))


def vector_norm(values: Sequence[float]) -> float:
    return math.sqrt(sum(float(v) * float(v) for v in values))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    na = vector_norm(a)
    nb = vector_norm(b)
    if na <= 0 or nb <= 0:
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    return dot / (na * nb)


def write_json_report(path: Path, payload: Dict[str, Any]) -> None:
    write_json(path, payload)


def write_md_report(path: Path, title: str, lines: List[str]) -> None:
    write_markdown(path, title, lines)


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_provider() -> Any:
    return create_embedding_provider("tongyi", "tongyi-embedding-vision-flash-2026-03-06")
