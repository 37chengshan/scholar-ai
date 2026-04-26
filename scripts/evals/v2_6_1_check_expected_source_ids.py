#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

from scripts.evals.v2_6_1_common import (
    DEFAULT_GOLDEN_PATH,
    ensure_output_dir,
    index_by_source_chunk_id,
    load_artifact_rows_by_stage,
    read_json,
    source_set,
    write_json_report,
    write_md_report,
)


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task A: expected source id existence")
    p.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    return p.parse_args()


def _find_artifact_record(
    sid: str,
    artifact_idx: Dict[str, Dict[str, Dict[str, Any]]],
) -> tuple[str, Dict[str, Any] | None]:
    for stage in ["raw", "rule", "llm"]:
        row = artifact_idx[stage].get(sid)
        if row is not None:
            return stage, row
    return "", None


def _find_collection_row(
    sid: str,
    collection_idx: Dict[str, Dict[str, Dict[str, Any]]],
) -> tuple[str, Dict[str, Any] | None]:
    for stage in ["raw", "rule", "llm"]:
        row = collection_idx[stage].get(sid)
        if row is not None:
            return stage, row
    return "", None


def _load_collections_from_ingest_report() -> Dict[str, Dict[str, Any]]:
    report_path = ROOT / "artifacts" / "benchmarks" / "v2_4" / "api_flash_ingest_report.json"
    payload = read_json(report_path)
    stages = payload.get("stages") or {}
    out: Dict[str, Dict[str, Any]] = {}
    for stage in ["raw", "rule", "llm"]:
        stat = stages.get(stage) or {}
        out[stage] = {
            "collection": str(stat.get("collection") or ""),
            "source_ids": set(),
            "index": {},
        }
    return out


def _load_collection_snapshot() -> Dict[str, Dict[str, Dict[str, Any]]]:
    from pymilvus import Collection, connections

    connections.connect(alias="v261_a", host="localhost", port=19530)
    result: Dict[str, Dict[str, Dict[str, Any]]] = {"raw": {}, "rule": {}, "llm": {}}
    for stage in ["raw", "rule", "llm"]:
        name = f"paper_contents_v2_api_tongyi_flash_{stage}_v2_4"
        col = Collection(name, using="v261_a")
        col.load()
        rows = col.query(
            expr="id >= 0",
            output_fields=["source_chunk_id", "paper_id", "content_type", "raw_data", "id"],
            limit=16384,
        )
        idx: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            sid = str(row.get("source_chunk_id") or "").strip()
            if sid:
                idx[sid] = row
        result[stage] = idx
    return result


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()

    golden = read_json(Path(args.golden_path))
    queries = list(golden.get("queries") or [])

    artifact_rows = load_artifact_rows_by_stage()
    artifact_idx = {stage: index_by_source_chunk_id(rows) for stage, rows in artifact_rows.items()}
    artifact_sets = {stage: source_set(rows) for stage, rows in artifact_rows.items()}

    collection_idx = _load_collection_snapshot()
    collection_sets = {stage: set(collection_idx[stage].keys()) for stage in ["raw", "rule", "llm"]}

    details: List[Dict[str, Any]] = []
    counters = Counter()
    category_flags: Set[str] = set()

    for item in queries:
        query_id = str(item.get("query_id") or "")
        expected_papers = {str(x) for x in (item.get("expected_paper_ids") or []) if str(x)}
        expected_content_types = {str(x) for x in (item.get("expected_content_types") or []) if str(x)}
        expected_source_ids = [str(x) for x in (item.get("expected_source_chunk_ids") or []) if str(x)]

        for sid in expected_source_ids:
            counters["expected_source_total"] += 1
            art_stage, art_row = _find_artifact_record(sid, artifact_idx)
            col_stage, col_row = _find_collection_row(sid, collection_idx)

            exists_artifact = art_row is not None
            exists_raw = sid in collection_sets["raw"]
            exists_rule = sid in collection_sets["rule"]
            exists_llm = sid in collection_sets["llm"]
            exists_any_collection = exists_raw or exists_rule or exists_llm

            issues: List[str] = []
            if not exists_any_collection:
                issues.append("expected_source_chunk_id_not_in_collection")
                category_flags.add("EVAL_ALIGNMENT_ERROR")
            if exists_artifact and not exists_any_collection:
                issues.append("artifact_has_but_collection_missing")
                category_flags.add("INGEST_ALIGNMENT_ERROR")
            if not exists_artifact and exists_any_collection:
                issues.append("collection_has_but_artifact_missing")
                category_flags.add("EVAL_ALIGNMENT_ERROR")

            paper_match = True
            content_type_match = True
            if expected_papers:
                candidate_paper = str((col_row or art_row or {}).get("paper_id") or "")
                paper_match = candidate_paper in expected_papers
                if not paper_match:
                    issues.append("expected_paper_id_mismatch")
                    category_flags.add("EVAL_ALIGNMENT_ERROR")
            if expected_content_types:
                candidate_type = str((col_row or art_row or {}).get("content_type") or "")
                content_type_match = candidate_type in expected_content_types
                if not content_type_match:
                    issues.append("expected_content_type_mismatch")
                    category_flags.add("EVAL_ALIGNMENT_ERROR")

            field_mix = False
            row_for_field = col_row or art_row or {}
            raw_data = row_for_field.get("raw_data") or {}
            if isinstance(raw_data, dict):
                global_id = str(raw_data.get("global_source_chunk_id") or "").strip()
                local_id = str(row_for_field.get("source_chunk_id") or "").strip()
                if global_id and global_id != local_id:
                    field_mix = True
                    issues.append("global_source_chunk_id_source_chunk_id_mixed")
                    category_flags.add("FIELD_MAPPING_ERROR")

            if issues:
                counters["with_issue"] += 1
                for issue in issues:
                    counters[f"issue::{issue}"] += 1
            else:
                counters["fully_aligned"] += 1

            details.append(
                {
                    "query_id": query_id,
                    "source_chunk_id": sid,
                    "exists_in_artifact": exists_artifact,
                    "exists_in_collection_raw": exists_raw,
                    "exists_in_collection_rule": exists_rule,
                    "exists_in_collection_llm": exists_llm,
                    "artifact_stage": art_stage,
                    "collection_stage": col_stage,
                    "paper_match": paper_match,
                    "content_type_match": content_type_match,
                    "field_mapping_mixed": field_mix,
                    "issues": issues,
                }
            )

    report = {
        "status": "PASS" if not category_flags else "BLOCKED",
        "blocked_categories": sorted(category_flags),
        "summary": {
            "expected_source_total": counters.get("expected_source_total", 0),
            "fully_aligned": counters.get("fully_aligned", 0),
            "with_issue": counters.get("with_issue", 0),
        },
        "issue_counts": {k.replace("issue::", ""): v for k, v in counters.items() if k.startswith("issue::")},
        "artifact_counts": {stage: len(artifact_sets[stage]) for stage in ["raw", "rule", "llm"]},
        "collection_counts": {stage: len(collection_sets[stage]) for stage in ["raw", "rule", "llm"]},
        "details": details,
    }

    json_path = out_dir / "source_chunk_id_existence_report.json"
    md_path = out_dir / "source_chunk_id_existence_report.md"
    write_json_report(json_path, report)

    lines = [
        f"- status: {report['status']}",
        f"- blocked_categories: {', '.join(report['blocked_categories']) if report['blocked_categories'] else 'none'}",
        f"- expected_source_total: {report['summary']['expected_source_total']}",
        f"- fully_aligned: {report['summary']['fully_aligned']}",
        f"- with_issue: {report['summary']['with_issue']}",
        "",
        "## Issue Counts",
    ]
    if report["issue_counts"]:
        for key, value in sorted(report["issue_counts"].items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Stage Source Chunk Counts",
        f"- artifact raw/rule/llm: {report['artifact_counts']['raw']} / {report['artifact_counts']['rule']} / {report['artifact_counts']['llm']}",
        f"- collection raw/rule/llm: {report['collection_counts']['raw']} / {report['collection_counts']['rule']} / {report['collection_counts']['llm']}",
    ])
    write_md_report(md_path, "Step6.1 Expected Source Chunk ID Existence", lines)
    print(json_path)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
