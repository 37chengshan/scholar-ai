#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection, connections

from scripts.evals.v2_6_1_common import DEFAULT_GOLDEN_PATH, ensure_output_dir, read_json, write_json_report, write_md_report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task D: oracle recall")
    p.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()
    payload = read_json(Path(args.golden_path))
    queries = list(payload.get("queries") or [])

    connections.connect(alias="v261_d", host=args.milvus_host, port=args.milvus_port)
    collections = {
        stage: Collection(f"paper_contents_v2_api_tongyi_flash_{stage}_{args.collection_suffix}", using="v261_d")
        for stage in ["raw", "rule", "llm"]
    }
    for col in collections.values():
        col.load()

    details: List[Dict[str, Any]] = []
    c = Counter()

    for q in queries:
        query_id = str(q.get("query_id") or "")
        expected_papers = set(str(x) for x in (q.get("expected_paper_ids") or []) if str(x))
        expected_types = set(str(x) for x in (q.get("expected_content_types") or []) if str(x))
        expected_sections = set(str(x) for x in (q.get("expected_sections") or []) if str(x))
        expected_sids = [str(x) for x in (q.get("expected_source_chunk_ids") or []) if str(x)]

        for sid in expected_sids:
            c["expected_total"] += 1
            stage_records: Dict[str, Any] = {}
            oracle_any = False
            hydration_fail = False
            data_mismatch = False

            for stage in ["raw", "rule", "llm"]:
                col = collections[stage]
                expr = f"source_chunk_id == '{_escape(sid)}'"
                rows = col.query(
                    expr=expr,
                    output_fields=["source_chunk_id", "paper_id", "content_type", "section", "page_num", "content_data"],
                    limit=5,
                )
                row = rows[0] if rows else {}
                exists = bool(rows)
                oracle_any = oracle_any or exists
                paper_ok = (not expected_papers) or (str(row.get("paper_id") or "") in expected_papers)
                type_ok = (not expected_types) or (str(row.get("content_type") or "") in expected_types)
                section_ok = (not expected_sections) or (str(row.get("section") or "") in expected_sections)
                content_non_empty = bool(str(row.get("content_data") or "").strip())
                hydration_fail = hydration_fail or (exists and not content_non_empty)
                data_mismatch = data_mismatch or (exists and (not paper_ok or not type_ok or not section_ok))

                stage_records[stage] = {
                    "exists": exists,
                    "paper_ok": paper_ok,
                    "content_type_ok": type_ok,
                    "section_ok": section_ok,
                    "content_data_non_empty": content_non_empty,
                }

            if oracle_any:
                c["oracle_exists"] += 1
            else:
                c["oracle_missing"] += 1
            if hydration_fail:
                c["hydration_fail"] += 1
            if data_mismatch:
                c["data_mismatch"] += 1

            details.append(
                {
                    "query_id": query_id,
                    "source_chunk_id": sid,
                    "stage_records": stage_records,
                    "oracle_exists_any_stage": oracle_any,
                    "hydration_fail": hydration_fail,
                    "data_mismatch": data_mismatch,
                }
            )

    blocked_categories: List[str] = []
    if c["oracle_missing"] > 0:
        blocked_categories.append("EVAL_ALIGNMENT_ERROR")
    if c["hydration_fail"] > 0:
        blocked_categories.append("RETRIEVAL_RUNTIME_ERROR")

    report = {
        "status": "PASS" if not blocked_categories else "BLOCKED",
        "blocked_categories": blocked_categories,
        "summary": {
            "expected_total": c["expected_total"],
            "oracle_exists": c["oracle_exists"],
            "oracle_missing": c["oracle_missing"],
            "hydration_fail": c["hydration_fail"],
            "data_mismatch": c["data_mismatch"],
        },
        "details": details,
    }

    json_path = out_dir / "oracle_recall_report.json"
    md_path = out_dir / "oracle_recall_report.md"
    write_json_report(json_path, report)
    lines = [
        f"- status: {report['status']}",
        f"- blocked_categories: {', '.join(report['blocked_categories']) if report['blocked_categories'] else 'none'}",
        f"- expected_total: {report['summary']['expected_total']}",
        f"- oracle_exists: {report['summary']['oracle_exists']}",
        f"- oracle_missing: {report['summary']['oracle_missing']}",
        f"- hydration_fail: {report['summary']['hydration_fail']}",
        f"- data_mismatch: {report['summary']['data_mismatch']}",
    ]
    write_md_report(md_path, "Step6.1 Oracle Recall Report", lines)
    print(json_path)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
