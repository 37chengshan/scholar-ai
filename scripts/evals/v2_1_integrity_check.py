#!/usr/bin/env python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.milvus_service import get_milvus_service


@dataclass(frozen=True)
class StageSpec:
    name: str
    collection: str


STAGES = [
    StageSpec("raw", "paper_contents_v2_qwen_v2_raw_v2_1"),
    StageSpec("rule", "paper_contents_v2_qwen_v2_rule_v2_1"),
    StageSpec("llm", "paper_contents_v2_qwen_v2_llm_v2_1"),
]


def _extract_source_chunk_id(row: dict[str, Any]) -> str:
    raw_data = row.get("raw_data") or {}
    if isinstance(raw_data, dict):
        source_chunk_id = str(raw_data.get("source_chunk_id") or "").strip()
        if source_chunk_id:
            return source_chunk_id
    return ""


def _extract_stage(row: dict[str, Any]) -> str:
    raw_data = row.get("raw_data") or {}
    if isinstance(raw_data, dict):
        return str(raw_data.get("stage") or "").strip()
    return ""


def _extract_section_path(row: dict[str, Any]) -> str:
    raw_data = row.get("raw_data") or {}
    if isinstance(raw_data, dict):
        for key in ("normalized_section_path", "raw_section_path", "section_path"):
            value = str(raw_data.get(key) or "").strip()
            if value:
                return value
    return str(row.get("section") or "").strip()


def _extract_raw_text(row: dict[str, Any]) -> str:
    raw_data = row.get("raw_data") or {}
    if isinstance(raw_data, dict):
        for key in ("raw_text", "text", "anchor_text"):
            value = raw_data.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _query_all_rows(collection_name: str, user_id: str) -> list[dict[str, Any]]:
    settings.MILVUS_COLLECTION_CONTENTS_V2 = collection_name
    service = get_milvus_service()
    service.connect()
    collection = service.get_collection(collection_name)

    rows: list[dict[str, Any]] = []
    last_id = 0
    page_size = 1000

    while True:
        expr = f'user_id == "{user_id}" and id > {last_id}'
        batch = collection.query(
            expr=expr,
            output_fields=[
                "id",
                "paper_id",
                "page_num",
                "section",
                "content_type",
                "content_data",
                "raw_data",
            ],
            limit=page_size,
        )
        if not batch:
            break
        rows.extend(batch)
        batch_max_id = max(int(item.get("id") or 0) for item in batch)
        if batch_max_id <= last_id:
            break
        last_id = batch_max_id
        if len(batch) < page_size:
            break

    return rows


def _stage_summary(rows: list[dict[str, Any]], stage_name: str) -> dict[str, Any]:
    source_ids = {_extract_source_chunk_id(row) for row in rows if _extract_source_chunk_id(row)}
    paper_ids = {str(row.get("paper_id") or "").strip() for row in rows if str(row.get("paper_id") or "").strip()}

    field_presence = {
        "paper_id": sum(1 for row in rows if str(row.get("paper_id") or "").strip()),
        "page_num": sum(1 for row in rows if int(row.get("page_num") or 0) > 0),
        "section_path": sum(1 for row in rows if _extract_section_path(row)),
        "content_type": sum(1 for row in rows if str(row.get("content_type") or "").strip()),
        "raw_text": sum(1 for row in rows if _extract_raw_text(row)),
        "content_data": sum(1 for row in rows if str(row.get("content_data") or "").strip()),
        "stage_metadata": sum(1 for row in rows if _extract_stage(row) == stage_name),
    }

    return {
        "row_count": len(rows),
        "paper_count": len(paper_ids),
        "source_chunk_count": len(source_ids),
        "paper_ids": sorted(paper_ids),
        "source_chunk_ids": sorted(source_ids),
        "field_presence": field_presence,
    }


def _write_markdown(report: dict[str, Any], output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Academic RAG v2.1 Integrity Report")
    lines.append("")
    lines.append(f"- user_id: {report['user_id']}")
    lines.append(f"- expected_chunks: {report['expected_chunks']}")
    lines.append(f"- expected_papers: {report['expected_papers']}")
    lines.append(f"- overall_status: {report['overall_status']}")
    lines.append("")
    lines.append("## Stage Counts")
    lines.append("")
    lines.append("| stage | row_count | source_chunk_count | paper_count | count_ok | paper_coverage_ok |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for stage_name, stage_report in report["stages"].items():
        checks = report["checks"][stage_name]
        lines.append(
            f"| {stage_name} | {stage_report['row_count']} | {stage_report['source_chunk_count']} | {stage_report['paper_count']} | {str(checks['count_ok'])} | {str(checks['paper_coverage_ok'])} |"
        )

    lines.append("")
    lines.append("## Alignment")
    lines.append("")
    lines.append(f"- source_chunk_alignment_ok: {report['alignment']['source_chunk_alignment_ok']}")
    lines.append(f"- raw_rule_diff_count: {report['alignment']['raw_rule_diff_count']}")
    lines.append(f"- raw_llm_diff_count: {report['alignment']['raw_llm_diff_count']}")
    lines.append("")
    lines.append("## Field Presence")
    lines.append("")
    lines.append("| stage | paper_id | page_num | section_path | content_type | raw_text | content_data | stage_metadata |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for stage_name, stage_report in report["stages"].items():
        fields = stage_report["field_presence"]
        lines.append(
            f"| {stage_name} | {fields['paper_id']} | {fields['page_num']} | {fields['section_path']} | {fields['content_type']} | {fields['raw_text']} | {fields['content_data']} | {fields['stage_metadata']} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    output_dir = ROOT / "artifacts" / "benchmarks" / "v2_1_20"
    output_dir.mkdir(parents=True, exist_ok=True)

    expected_chunks = 1451
    expected_papers = 20
    user_id = "benchmark-user"

    stage_rows: dict[str, list[dict[str, Any]]] = {}
    stage_reports: dict[str, dict[str, Any]] = {}
    checks: dict[str, dict[str, Any]] = {}

    for spec in STAGES:
        rows = _query_all_rows(spec.collection, user_id=user_id)
        stage_rows[spec.name] = rows
        stage_reports[spec.name] = _stage_summary(rows, spec.name)
        checks[spec.name] = {
            "count_ok": stage_reports[spec.name]["row_count"] == expected_chunks,
            "paper_coverage_ok": stage_reports[spec.name]["paper_count"] == expected_papers,
        }

    raw_ids = set(stage_reports["raw"]["source_chunk_ids"])
    rule_ids = set(stage_reports["rule"]["source_chunk_ids"])
    llm_ids = set(stage_reports["llm"]["source_chunk_ids"])

    alignment = {
        "source_chunk_alignment_ok": raw_ids == rule_ids == llm_ids,
        "raw_rule_diff_count": len(raw_ids.symmetric_difference(rule_ids)),
        "raw_llm_diff_count": len(raw_ids.symmetric_difference(llm_ids)),
        "raw_rule_diff_examples": sorted(list(raw_ids.symmetric_difference(rule_ids)))[:20],
        "raw_llm_diff_examples": sorted(list(raw_ids.symmetric_difference(llm_ids)))[:20],
    }

    overall_status = "PASS"
    for stage_name in checks:
        if not checks[stage_name]["count_ok"] or not checks[stage_name]["paper_coverage_ok"]:
            overall_status = "BLOCKED"
            break
    if overall_status == "PASS" and not alignment["source_chunk_alignment_ok"]:
        overall_status = "BLOCKED"

    report = {
        "user_id": user_id,
        "expected_chunks": expected_chunks,
        "expected_papers": expected_papers,
        "overall_status": overall_status,
        "stages": stage_reports,
        "checks": checks,
        "alignment": alignment,
    }

    json_path = output_dir / "integrity_report.json"
    md_path = output_dir / "integrity_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)

    print(f"integrity_json={json_path}")
    print(f"integrity_md={md_path}")
    print(f"overall_status={overall_status}")


if __name__ == "__main__":
    main()
