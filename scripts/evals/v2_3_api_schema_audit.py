#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection, connections, utility

ROOT = Path(__file__).resolve().parents[2]

TARGET_COLLECTIONS_FLASH = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}
SOURCE_COLLECTIONS = {
    "raw": "paper_contents_v2_qwen_v2_raw_v2_1",
    "rule": "paper_contents_v2_qwen_v2_rule_v2_1",
    "llm": "paper_contents_v2_qwen_v2_llm_v2_1",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.3 api schema audit")
    p.add_argument("--expected-dim", type=int, required=True)
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3"))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    connections.connect(alias="v23_audit", host=args.milvus_host, port=args.milvus_port)

    report: Dict[str, Any] = {
        "expected_dim": args.expected_dim,
        "collections": {},
        "status": "PASS",
        "error": None,
    }

    try:
        for stage, name in TARGET_COLLECTIONS_FLASH.items():
            if not utility.has_collection(name, using="v23_audit"):
                raise RuntimeError(f"collection missing: {name}")

            col = Collection(name, using="v23_audit")
            source = Collection(SOURCE_COLLECTIONS[stage], using="v23_audit")
            col.load()
            count = col.num_entities

            dim = 0
            for f in col.schema.fields:
                if f.name == "embedding":
                    dim = int(f.params.get("dim", 0))
                    break

            rows = col.query(expr="id >= 0", output_fields=["paper_id", "source_chunk_id"], limit=5000)
            source_rows = source.query(expr="id >= 0", output_fields=["id"], limit=5000)
            papers = sorted({r.get("paper_id", "") for r in rows if r.get("paper_id")})
            source_ids = {r.get("source_chunk_id", "") for r in rows if r.get("source_chunk_id")}
            expected_source_ids = {str(r.get("id") or "") for r in source_rows if r.get("id") is not None}

            ok = (
                count == 1451
                and dim == args.expected_dim
                and len(papers) == 20
                and len(source_ids) == 1451
                and source_ids == expected_source_ids
            )
            report["collections"][stage] = {
                "name": name,
                "entity_count": count,
                "dim": dim,
                "paper_coverage": len(papers),
                "source_chunk_id_coverage": len(source_ids),
                "source_chunk_id_aligned": source_ids == expected_source_ids,
                "ok": ok,
            }

            if not ok:
                raise RuntimeError(f"schema gate failed for {stage}")

    except Exception as e:
        report["status"] = "BLOCKED"
        report["error"] = str(e)

    (out_dir / "api_flash_schema_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# v2.3 API Flash Schema Audit", "", f"- status: {report['status']}", "", "| stage | entity_count | dim | papers | source_chunk_ids | ok |", "|---|---:|---:|---:|---:|---|",]
    for stage, stat in report.get("collections", {}).items():
        lines.append(f"| {stage} | {stat['entity_count']} | {stat['dim']} | {stat['paper_coverage']} | {stat['source_chunk_id_coverage']} | {stat['ok']} |")
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    (out_dir / "api_flash_schema_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
