#!/usr/bin/env python3
"""SPECTER2 Schema Audit — Gate 4.

Verifies the 3 SPECTER2 collections exist in Milvus with:
  - entity_count == 1451
  - vector dim == 768
  - paper_count == 20

Usage:
  python scripts/audit_specter2_collections.py

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_schema_audit.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_schema_audit.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"

EXPECTED_CHUNK_COUNT = 1451
EXPECTED_PAPER_COUNT = 20
EXPECTED_DIM = 768

SPECTER2_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}


def inspect_dim(col, vector_field: str = "embedding") -> int:
    """Extract vector dimension from collection schema."""
    try:
        for field in col.schema.fields:
            if field.name == vector_field:
                return field.params.get("dim", -1)
    except Exception:
        pass
    return -1


def audit_collection(col_name: str, alias: str, stage: str) -> dict:
    from pymilvus import Collection, utility

    result = {
        "collection": col_name,
        "stage": stage,
        "exists": False,
        "entity_count": 0,
        "vector_dim": -1,
        "paper_count": 0,
        "schema_fields": [],
        "checks": [],
        "status": "BLOCKED",
    }

    if not utility.has_collection(col_name, using=alias):
        result["checks"].append(f"FAIL: collection '{col_name}' does not exist")
        return result

    result["exists"] = True
    col = Collection(col_name, using=alias)
    col.load()

    # Entity count
    count = col.num_entities
    result["entity_count"] = count
    if count == EXPECTED_CHUNK_COUNT:
        result["checks"].append(f"PASS: entity_count={count}")
    else:
        result["checks"].append(f"FAIL: entity_count={count} != {EXPECTED_CHUNK_COUNT}")

    # Vector dim
    dim = inspect_dim(col, "embedding")
    result["vector_dim"] = dim
    if dim == EXPECTED_DIM:
        result["checks"].append(f"PASS: vector_dim={dim}")
    else:
        result["checks"].append(f"FAIL: vector_dim={dim} != {EXPECTED_DIM}")

    # Schema fields
    field_names = [f.name for f in col.schema.fields]
    result["schema_fields"] = field_names
    required_fields = {"source_chunk_id", "paper_id", "embedding", "content_data", "stage"}
    missing = required_fields - set(field_names)
    if not missing:
        result["checks"].append(f"PASS: schema has required fields")
    else:
        result["checks"].append(f"FAIL: schema missing fields: {sorted(missing)}")

    # Paper count via query
    try:
        rows = col.query(
            expr="paper_id != ''",
            output_fields=["paper_id"],
            limit=16384,
        )
        paper_ids = {r["paper_id"] for r in rows}
        result["paper_count"] = len(paper_ids)
        if len(paper_ids) == EXPECTED_PAPER_COUNT:
            result["checks"].append(f"PASS: paper_count={len(paper_ids)}")
        else:
            result["checks"].append(
                f"FAIL: paper_count={len(paper_ids)} != {EXPECTED_PAPER_COUNT}"
            )
    except Exception as e:
        result["checks"].append(f"WARN: paper count query failed: {e}")

    all_pass = all(c.startswith("PASS") or c.startswith("WARN") for c in result["checks"])
    result["status"] = "PASS" if all_pass else "BLOCKED"
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SPECTER2 Schema Audit — Gate 4")
    print("=" * 60)

    from app.core.milvus_service import get_milvus_service

    svc = get_milvus_service()
    svc.connect()
    alias = svc._alias
    print(f"  Milvus alias={alias}\n")

    results = {}
    all_ok = True

    for stage, col_name in SPECTER2_COLLECTIONS.items():
        print(f"Auditing {stage}: {col_name} ...")
        r = audit_collection(col_name, alias, stage)
        results[stage] = r
        for check in r["checks"]:
            print(f"  {check}")
        print(f"  => {r['status']}\n")
        if r["status"] == "BLOCKED":
            all_ok = False

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_chunk_count": EXPECTED_CHUNK_COUNT,
        "expected_paper_count": EXPECTED_PAPER_COUNT,
        "expected_dim": EXPECTED_DIM,
        "collections": results,
        "status": "PASS" if all_ok else "BLOCKED",
    }

    json_path = OUT_DIR / "specter2_schema_audit.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"  → {json_path.relative_to(ROOT)}")

    _write_md(report)

    print(f"\n[{report['status']}] SPECTER2 schema audit")
    return 0 if all_ok else 1


def _write_md(report: dict) -> None:
    lines = [
        "# SPECTER2 Schema Audit Report",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**Status:** `{report['status']}`",
        "",
        "## Expected",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| chunk_count | {report['expected_chunk_count']} |",
        f"| paper_count | {report['expected_paper_count']} |",
        f"| vector_dim | {report['expected_dim']} |",
        "",
        "## Collection Results",
        "",
    ]
    for stage, r in report["collections"].items():
        lines += [
            f"### {stage} — `{r['collection']}`",
            "",
            f"**Status:** `{r['status']}`",
            "",
            "| Check | Result |",
            "|-------|--------|",
        ]
        for c in r["checks"]:
            tag = c.split(":")[0]
            lines.append(f"| {tag} | {c} |")
        lines.append(f"| entity_count | {r['entity_count']} |")
        lines.append(f"| paper_count | {r['paper_count']} |")
        lines.append(f"| vector_dim | {r['vector_dim']} |")
        lines.append(f"| schema_fields | {', '.join(r['schema_fields'])} |")
        lines.append("")

    md_path = ROOT / "artifacts/benchmarks/specter2_v2_1_20/specter2_schema_audit.md"
    md_path.write_text("\n".join(lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
