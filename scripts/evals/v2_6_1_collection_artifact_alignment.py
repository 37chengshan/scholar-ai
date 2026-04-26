#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

from pymilvus import Collection, connections

from scripts.evals.v2_6_1_common import (
    ensure_output_dir,
    load_artifact_rows_by_stage,
    source_set,
    write_json_report,
    write_md_report,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task B: artifact vs collection alignment")
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _dist(rows: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    c = Counter()
    for row in rows:
        value = str(row.get(field) or "").strip() or "<empty>"
        c[value] += 1
    return dict(sorted(c.items(), key=lambda kv: kv[0]))


def _collection_rows(alias: str, name: str) -> List[Dict[str, Any]]:
    col = Collection(name, using=alias)
    col.load()
    return list(
        col.query(
            expr="id >= 0",
            output_fields=["source_chunk_id", "paper_id", "user_id", "indexable"],
            limit=16384,
        )
    )


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()
    artifact_rows = load_artifact_rows_by_stage()
    artifact_sets = {stage: source_set(rows) for stage, rows in artifact_rows.items()}

    connections.connect(alias="v261_b", host=args.milvus_host, port=args.milvus_port)

    per_stage: Dict[str, Any] = {}
    blocked = False

    for stage in ["raw", "rule", "llm"]:
        collection_name = f"paper_contents_v2_api_tongyi_flash_{stage}_{args.collection_suffix}"
        rows = _collection_rows("v261_b", collection_name)
        collection_ids = [str(r.get("source_chunk_id") or "").strip() for r in rows if str(r.get("source_chunk_id") or "").strip()]
        collection_set = set(collection_ids)
        artifact_set = artifact_sets.get(stage, set())

        intersection = artifact_set & collection_set
        missing_in_collection = sorted(artifact_set - collection_set)
        extra_in_collection = sorted(collection_set - artifact_set)

        id_counter = Counter(collection_ids)
        duplicate = {k: v for k, v in id_counter.items() if v > 1}

        ratio = round(len(intersection) / max(len(artifact_set), 1), 6)
        stage_pass = ratio == 1.0 and not missing_in_collection and not duplicate
        if not stage_pass:
            blocked = True

        per_stage[stage] = {
            "collection": collection_name,
            "artifact_count": len(artifact_set),
            "collection_count": len(collection_set),
            "intersection_count": len(intersection),
            "intersection_ratio": ratio,
            "missing_in_collection_count": len(missing_in_collection),
            "missing_in_collection_preview": missing_in_collection[:20],
            "extra_in_collection_count": len(extra_in_collection),
            "extra_in_collection_preview": extra_in_collection[:20],
            "duplicate_in_collection_count": len(duplicate),
            "duplicate_in_collection_preview": dict(list(duplicate.items())[:20]),
            "paper_id_distribution": _dist(rows, "paper_id"),
            "user_id_distribution": _dist(rows, "user_id"),
            "indexable_distribution": _dist(rows, "indexable"),
            "status": "PASS" if stage_pass else "BLOCKED",
        }

    stage_sets_equal = (
        artifact_sets["raw"] == artifact_sets["rule"] == artifact_sets["llm"]
        and per_stage["raw"]["collection_count"] == per_stage["rule"]["collection_count"] == per_stage["llm"]["collection_count"]
        and per_stage["raw"]["intersection_count"] == per_stage["rule"]["intersection_count"] == per_stage["llm"]["intersection_count"]
    )
    if not stage_sets_equal:
        blocked = True

    report = {
        "status": "PASS" if not blocked else "BLOCKED",
        "pass_criteria": {
            "intersection_count_over_artifact_count_equals_1": not blocked,
            "duplicate_in_collection_equals_0": all(per_stage[s]["duplicate_in_collection_count"] == 0 for s in ["raw", "rule", "llm"]),
            "missing_in_collection_equals_0": all(per_stage[s]["missing_in_collection_count"] == 0 for s in ["raw", "rule", "llm"]),
            "raw_rule_llm_source_set_consistent": stage_sets_equal,
        },
        "stages": per_stage,
    }

    json_path = out_dir / "collection_artifact_alignment_report.json"
    md_path = out_dir / "collection_artifact_alignment_report.md"
    write_json_report(json_path, report)

    lines = [f"- status: {report['status']}", "", "## Stage Summary", "", "| stage | artifact | collection | intersection | missing | extra | duplicates | status |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for stage in ["raw", "rule", "llm"]:
        stat = per_stage[stage]
        lines.append(
            f"| {stage} | {stat['artifact_count']} | {stat['collection_count']} | {stat['intersection_count']} | {stat['missing_in_collection_count']} | {stat['extra_in_collection_count']} | {stat['duplicate_in_collection_count']} | {stat['status']} |"
        )

    lines.extend(["", "## Pass Criteria"])
    for key, value in report["pass_criteria"].items():
        lines.append(f"- {key}: {value}")

    write_md_report(md_path, "Step6.1 Collection vs Artifact Alignment", lines)
    print(json_path)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
