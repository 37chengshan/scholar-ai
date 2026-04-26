#!/usr/bin/env python
"""Audit Milvus schemas for Academic RAG v2.1.1 retrieval infrastructure.

Outputs:
- artifacts/benchmarks/v2_1_20/milvus_schema_audit.json
- artifacts/benchmarks/v2_1_20/milvus_schema_audit.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, connections, utility


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_1_20"
DEFAULT_COLLECTIONS = [
    "paper_contents_v2_qwen_v2_raw_v2_1",
    "paper_contents_v2_qwen_v2_rule_v2_1",
    "paper_contents_v2_qwen_v2_llm_v2_1",
]

SAFE_OUTPUT_FIELDS = [
    "paper_id",
    "user_id",
    "page_num",
    "content_type",
    "section",
    "content_data",
    "raw_data",
    "indexable",
    "embedding_status",
]


@dataclass(frozen=True)
class AuditResult:
    collection: str
    exists: bool
    loaded: bool
    entity_count: int
    primary_key: str
    vector_fields: list[dict[str, Any]]
    scalar_fields: list[str]
    json_fields: list[str]
    dynamic_field_enabled: bool
    indexes: list[dict[str, Any]]
    safe_output_fields: list[str]
    unsafe_or_unknown_fields: list[str]
    checks: dict[str, bool]
    errors: list[str]


def _dtype_name(dtype: Any) -> str:
    try:
        return DataType(dtype).name
    except Exception:
        return str(dtype)


def _schema_for_collection(collection_name: str) -> CollectionSchema | None:
    if not utility.has_collection(collection_name):
        return None
    collection = Collection(collection_name)
    return collection.schema


def _audit_collection(collection_name: str, expected_count: int) -> AuditResult:
    exists = utility.has_collection(collection_name)
    if not exists:
        return AuditResult(
            collection=collection_name,
            exists=False,
            loaded=False,
            entity_count=0,
            primary_key="",
            vector_fields=[],
            scalar_fields=[],
            json_fields=[],
            dynamic_field_enabled=False,
            indexes=[],
            safe_output_fields=[],
            unsafe_or_unknown_fields=[],
            checks={
                "collection_exists": False,
                "has_vector_field": False,
                "vector_dim_present": False,
                "entity_count_expected": False,
            },
            errors=[f"Collection not found: {collection_name}"],
        )

    collection = Collection(collection_name)
    loaded = False
    errors: list[str] = []

    try:
        collection.load()
        loaded = True
    except Exception as exc:
        errors.append(f"Failed to load collection: {exc}")

    schema = collection.schema
    fields = list(schema.fields)
    field_names = [field.name for field in fields]

    primary_key = ""
    vector_fields: list[dict[str, Any]] = []
    scalar_fields: list[str] = []
    json_fields: list[str] = []

    for field in fields:
        if getattr(field, "is_primary", False):
            primary_key = field.name

        dtype = _dtype_name(field.dtype)
        if dtype == "FLOAT_VECTOR":
            dim = None
            params = getattr(field, "params", None)
            if isinstance(params, dict):
                dim = params.get("dim")
            vector_fields.append(
                {
                    "name": field.name,
                    "dtype": dtype,
                    "dim": int(dim) if dim is not None else None,
                }
            )
        elif dtype == "JSON":
            json_fields.append(field.name)
        else:
            scalar_fields.append(field.name)

    indexes: list[dict[str, Any]] = []
    try:
        for idx in collection.indexes:
            idx_params = getattr(idx, "params", {}) or {}
            indexes.append(
                {
                    "field": getattr(idx, "field_name", ""),
                    "index_name": getattr(idx, "index_name", ""),
                    "index_type": idx_params.get("index_type") or idx_params.get("index_name") or "",
                    "metric_type": idx_params.get("metric_type") or "",
                }
            )
    except Exception as exc:
        errors.append(f"Failed to inspect indexes: {exc}")

    has_dynamic = bool(getattr(schema, "enable_dynamic_field", False))
    safe_fields = [field for field in SAFE_OUTPUT_FIELDS if field in field_names]
    unsafe_fields = [field for field in SAFE_OUTPUT_FIELDS if field not in field_names]

    entity_count = int(collection.num_entities)
    has_vector_field = bool(vector_fields)
    vector_dim_present = any(v.get("dim") for v in vector_fields)
    count_ok = entity_count == expected_count

    if not has_vector_field:
        errors.append("No FLOAT_VECTOR field found")
    if not vector_dim_present:
        errors.append("Vector field found but dim missing")
    if not count_ok:
        errors.append(
            f"Entity count mismatch: expected {expected_count}, got {entity_count}"
        )

    return AuditResult(
        collection=collection_name,
        exists=True,
        loaded=loaded,
        entity_count=entity_count,
        primary_key=primary_key,
        vector_fields=vector_fields,
        scalar_fields=scalar_fields,
        json_fields=json_fields,
        dynamic_field_enabled=has_dynamic,
        indexes=indexes,
        safe_output_fields=safe_fields,
        unsafe_or_unknown_fields=unsafe_fields,
        checks={
            "collection_exists": True,
            "has_vector_field": has_vector_field,
            "vector_dim_present": vector_dim_present,
            "entity_count_expected": count_ok,
        },
        errors=errors,
    )


def _markdown_report(results: list[AuditResult], overall_status: str) -> str:
    lines: list[str] = []
    lines.append("# Milvus Schema Audit (v2.1.1)")
    lines.append("")
    lines.append(f"- Overall Status: {overall_status}")
    lines.append("")
    lines.append("| collection | exists | loaded | entity_count | vector_fields | dims | status |")
    lines.append("|---|---|---|---:|---:|---|---|")

    for item in results:
        dims = ",".join(
            str(v.get("dim")) for v in item.vector_fields if v.get("dim") is not None
        )
        status = "PASS" if not item.errors else "FAIL"
        lines.append(
            f"| {item.collection} | {item.exists} | {item.loaded} | {item.entity_count} | "
            f"{len(item.vector_fields)} | {dims or '-'} | {status} |"
        )

    lines.append("")
    for item in results:
        lines.append(f"## {item.collection}")
        lines.append("")
        lines.append(f"- primary_key: {item.primary_key or '-'}")
        lines.append(f"- dynamic_field_enabled: {item.dynamic_field_enabled}")
        lines.append(f"- safe_output_fields: {item.safe_output_fields}")
        lines.append(f"- unsafe_or_unknown_fields: {item.unsafe_or_unknown_fields}")
        if item.errors:
            lines.append("- errors:")
            for err in item.errors:
                lines.append(f"  - {err}")
        else:
            lines.append("- errors: []")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milvus collection schemas")
    parser.add_argument(
        "--collections",
        nargs="*",
        default=DEFAULT_COLLECTIONS,
        help="Collection names to audit",
    )
    parser.add_argument(
        "--expected-entity-count",
        type=int,
        default=1451,
        help="Expected entity count for each collection",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory",
    )
    parser.add_argument("--host", default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    args = parser.parse_args()

    connections.connect(host=args.host, port=args.port)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [_audit_collection(name, args.expected_entity_count) for name in args.collections]
    overall_status = "PASS" if all(not item.errors for item in results) else "FAIL"

    payload = {
        "overall_status": overall_status,
        "expected_entity_count": args.expected_entity_count,
        "collections": [
            {
                "collection": item.collection,
                "exists": item.exists,
                "loaded": item.loaded,
                "entity_count": item.entity_count,
                "primary_key": item.primary_key,
                "vector_fields": item.vector_fields,
                "scalar_fields": item.scalar_fields,
                "json_fields": item.json_fields,
                "dynamic_field_enabled": item.dynamic_field_enabled,
                "indexes": item.indexes,
                "safe_output_fields": item.safe_output_fields,
                "unsafe_or_unknown_fields": item.unsafe_or_unknown_fields,
                "checks": item.checks,
                "errors": item.errors,
            }
            for item in results
        ],
    }

    json_path = out_dir / "milvus_schema_audit.json"
    md_path = out_dir / "milvus_schema_audit.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_report(results, overall_status), encoding="utf-8")

    print(f"schema_audit_json={json_path}")
    print(f"schema_audit_md={md_path}")
    print(f"overall_status={overall_status}")

    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
