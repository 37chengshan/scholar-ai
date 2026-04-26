#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from pymilvus import Collection, connections, utility

from scripts.evals.v2_4_common import (
    DEFAULT_OUTPUT_DIR,
    OFFICIAL_OUTPUT_FIELDS,
    REQUIRED_SCHEMA_FIELDS,
    ensure_query_dim_matches_collection_dim,
    read_json,
    source_chunk_set,
    stage_collection_name,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 API flash schema audit")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _schema_field_names(col: Collection) -> Set[str]:
    return {getattr(f, "name", "") for f in getattr(col.schema, "fields", [])}


def _collection_dim(col: Collection) -> int:
    for f in col.schema.fields:
        if getattr(f, "name", "") == "embedding":
            return int((getattr(f, "params", {}) or {}).get("dim", 0))
    return 0


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    probe_path = out_dir / "provider_probe.json"
    if not probe_path.exists():
        report = {"status": "BLOCKED", "error": "provider_probe_missing"}
        write_json(out_dir / "api_flash_schema_audit.json", report)
        write_markdown(out_dir / "api_flash_schema_audit.md", "v2.4 API Flash Schema Audit", ["- status: BLOCKED", "- error: provider_probe_missing"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    probe = read_json(probe_path)
    expected_dim = int(probe.get("dimension") or 0)

    connections.connect(alias="v24_schema_audit", host=args.milvus_host, port=args.milvus_port)

    report: Dict[str, Any] = {
        "expected_dim": expected_dim,
        "collections": {},
        "source_chunk_id_alignment": False,
        "status": "PASS",
        "error": None,
    }

    try:
        stage_sets: Dict[str, Set[str]] = {}
        for stage in ["raw", "rule", "llm"]:
            name = stage_collection_name(stage, args.collection_suffix)
            if not utility.has_collection(name, using="v24_schema_audit"):
                raise RuntimeError(f"collection_missing:{name}")
            col = Collection(name, using="v24_schema_audit")
            col.load()

            dim = _collection_dim(col)
            ensure_query_dim_matches_collection_dim(expected_dim, dim)

            field_names = _schema_field_names(col)
            missing_fields = [f for f in REQUIRED_SCHEMA_FIELDS if f not in field_names]
            if missing_fields:
                raise RuntimeError(f"required_fields_missing:{name}:{','.join(missing_fields)}")

            rows = col.query(expr="id >= 0", output_fields=["source_chunk_id", "paper_id"], limit=16384)
            ids = source_chunk_set(rows)
            paper_ids = {str(r.get("paper_id") or "") for r in rows if str(r.get("paper_id") or "")}

            # Official search output fields should be first-class fields (not raw_data dependent)
            missing_official = [f for f in OFFICIAL_OUTPUT_FIELDS if f not in field_names]
            if missing_official:
                raise RuntimeError(f"official_output_fields_missing:{name}:{','.join(missing_official)}")

            # index loaded quick check
            has_embedding_index = any(getattr(idx, "field_name", "") == "embedding" for idx in col.indexes)
            if not has_embedding_index:
                raise RuntimeError(f"embedding_index_missing:{name}")

            stage_sets[stage] = ids
            report["collections"][stage] = {
                "name": name,
                "exists": True,
                "entity_count": col.num_entities,
                "vector_dim": dim,
                "source_chunk_id_count": len(ids),
                "source_chunk_id_unique": len(ids) == col.num_entities,
                "paper_count": len(paper_ids),
                "required_fields_missing": missing_fields,
                "official_output_fields_missing": missing_official,
                "index_loaded": has_embedding_index,
            }

        report["source_chunk_id_alignment"] = (
            stage_sets["raw"] == stage_sets["rule"] and stage_sets["raw"] == stage_sets["llm"]
        )
        if not report["source_chunk_id_alignment"]:
            raise RuntimeError("source_chunk_id_alignment_failed")

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)

    write_json(out_dir / "api_flash_schema_audit.json", report)
    lines = [
        f"- expected_dim: {report['expected_dim']}",
        f"- source_chunk_id_alignment: {report.get('source_chunk_id_alignment')}",
        f"- status: {report['status']}",
        "",
        "| stage | entity_count | vector_dim | source_chunk_id_count | paper_count | index_loaded |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for stage, stat in report.get("collections", {}).items():
        lines.append(
            f"| {stage} | {stat.get('entity_count',0)} | {stat.get('vector_dim',0)} | {stat.get('source_chunk_id_count',0)} | {stat.get('paper_count',0)} | {stat.get('index_loaded',False)} |"
        )
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    write_markdown(out_dir / "api_flash_schema_audit.md", "v2.4 API Flash Schema Audit", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
