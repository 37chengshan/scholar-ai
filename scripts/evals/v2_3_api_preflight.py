#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from pymilvus import Collection, connections

ROOT = Path(__file__).resolve().parents[2]

TARGET_COLLECTIONS_FLASH = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.3 api preflight")
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3"))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def run_id_only_search(col: Collection) -> bool:
    sample = col.query(expr="id >= 0", output_fields=["embedding"], limit=1)
    if not sample:
        return False
    vec = sample[0].get("embedding")
    if not vec:
        return False

    res = col.search(
        data=[vec],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=3,
        output_fields=[],
    )
    return bool(res and res[0])


def run_hydration_check(col: Collection) -> bool:
    sample = col.query(expr="id >= 0", output_fields=["embedding"], limit=1)
    if not sample:
        return False
    vec = sample[0].get("embedding")
    if not vec:
        return False

    res = col.search(
        data=[vec],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=3,
        output_fields=["paper_id", "source_chunk_id", "content_data"],
    )
    if not res or not res[0]:
        return False
    first = res[0][0]
    fields = {}
    if hasattr(first, "fields") and first.fields:
        fields = first.fields
    elif hasattr(first, "entity") and hasattr(first.entity, "get"):
        fields = first.entity
    paper_id = str(fields.get("paper_id") or "")
    source_chunk_id = str(fields.get("source_chunk_id") or "")
    content_data = str(fields.get("content_data") or "")
    return bool(paper_id and source_chunk_id and content_data)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    connections.connect(alias="v23_preflight", host=args.milvus_host, port=args.milvus_port)

    report: Dict[str, Any] = {
        "fallback_used": False,
        "collections": {},
        "status": "PASS",
        "error": None,
    }

    try:
        for stage, name in TARGET_COLLECTIONS_FLASH.items():
            col = Collection(name, using="v23_preflight")
            col.load()
            id_only_ok = run_id_only_search(col)
            hydration_ok = run_hydration_check(col)
            ok = id_only_ok and hydration_ok
            report["collections"][stage] = {
                "name": name,
                "id_only_search_ok": id_only_ok,
                "hydration_ok": hydration_ok,
                "ok": ok,
            }
            if not ok:
                raise RuntimeError(f"preflight failed for {stage}")

    except Exception as e:
        report["status"] = "BLOCKED"
        report["error"] = str(e)

    (out_dir / "api_flash_preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# v2.3 API Flash Preflight",
        "",
        f"- status: {report['status']}",
        f"- fallback_used: {report['fallback_used']}",
        "",
        "| stage | id_only_search_ok | hydration_ok | ok |",
        "|---|---|---|---|",
    ]
    for stage, stat in report.get("collections", {}).items():
        lines.append(f"| {stage} | {stat['id_only_search_ok']} | {stat['hydration_ok']} | {stat['ok']} |")
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    (out_dir / "api_flash_preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
