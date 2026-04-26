#!/usr/bin/env python
from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path
from typing import Any
import sys

from pymilvus import Collection, connections

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.retrieval_branch_registry import infer_stage_from_collection

DEFAULT_COLLECTIONS = [
    "paper_contents_v2_qwen_v2_raw_v2_1",
    "paper_contents_v2_qwen_v2_rule_v2_1",
    "paper_contents_v2_qwen_v2_llm_v2_1",
]

BASE_FIELDS = ["paper_id", "page_num", "content_type"]
EXTRA_FIELDS = ["section", "content_data", "raw_data", "indexable", "embedding_status"]


def _is_unsupported(exc: Exception) -> bool:
    return "unsupported field type" in str(exc).lower()


def _build_probe_vector(collection: Collection) -> list[float]:
    dim = 0
    for field in collection.schema.fields:
        if field.name == "embedding":
            dim = int((field.params or {}).get("dim") or 0)
            break
    if dim <= 0:
        raise ValueError(f"collection={collection.name} missing embedding dim")

    expr = "paper_id != ''"
    rows = collection.query(expr=expr, output_fields=["embedding"], limit=1)
    if rows and rows[0].get("embedding"):
        return list(rows[0]["embedding"])

    return [random.uniform(-0.01, 0.01) for _ in range(dim)]


def _run_search(collection: Collection, vector: list[float], fields: list[str]) -> dict[str, Any]:
    expr = "paper_id != ''"
    try:
        collection.search(
            data=[vector],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=1,
            expr=expr,
            output_fields=fields,
        )
        return {"ok": True, "unsupported": False, "error": ""}
    except Exception as exc:
        return {
            "ok": False,
            "unsupported": _is_unsupported(exc),
            "error": str(exc),
        }


def _find_minimal_failing_set(collection: Collection, vector: list[float], available_extras: list[str]) -> list[str]:
    if not available_extras:
        return []

    for size in range(1, len(available_extras) + 1):
        for combo in itertools.combinations(available_extras, size):
            fields = BASE_FIELDS + list(combo)
            result = _run_search(collection, vector, fields)
            if result["unsupported"]:
                return list(combo)
    return []


def _to_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# v2.1.2 Milvus output_fields 诊断")
    lines.append("")
    lines.append(f"- overall_status: {report['overall_status']}")
    lines.append("")

    for item in report["collections"]:
        lines.append(f"## {item['collection']}")
        lines.append("")
        lines.append(f"- stage: {item['stage']}")
        lines.append(f"- unsupported_seen: {item['unsupported_seen']}")
        lines.append(f"- minimal_failing_extra_fields: {item['minimal_failing_extra_fields']}")
        lines.append("")
        lines.append("| name | fields | ok | unsupported |")
        lines.append("|---|---|---|---|")
        for test in item["tests"]:
            lines.append(
                f"| {test['name']} | {test['fields']} | {test['ok']} | {test['unsupported']} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Milvus output_fields unsupported field type")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=19530)
    parser.add_argument("--collections", nargs="*", default=DEFAULT_COLLECTIONS)
    parser.add_argument(
        "--output-json",
        default="artifacts/benchmarks/v2_1_20/output_fields_diag_v2_1_2.json",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/benchmarks/v2_1_20/output_fields_diag_v2_1_2.md",
    )
    args = parser.parse_args()

    connections.connect(alias="diag", host=args.host, port=args.port)

    report_items: list[dict[str, Any]] = []
    overall_status = "PASS"

    for name in args.collections:
        collection = Collection(name, using="diag")
        schema_names = {f.name for f in collection.schema.fields}
        vector = _build_probe_vector(collection)

        tests: list[dict[str, Any]] = []

        test_sets: list[tuple[str, list[str]]] = [
            ("empty", []),
            ("paper_only", ["paper_id"]),
            ("base_triplet", BASE_FIELDS.copy()),
        ]

        progressive = BASE_FIELDS.copy()
        for field in EXTRA_FIELDS:
            if field not in schema_names:
                tests.append(
                    {
                        "name": f"add_{field}",
                        "fields": progressive + [field],
                        "ok": False,
                        "unsupported": False,
                        "error": "SKIP_NOT_IN_SCHEMA",
                    }
                )
                continue
            progressive = progressive + [field]
            test_sets.append((f"add_{field}", progressive.copy()))

        for test_name, fields in test_sets:
            result = _run_search(collection, vector, fields)
            tests.append(
                {
                    "name": test_name,
                    "fields": fields,
                    **result,
                }
            )

        available_extras = [f for f in EXTRA_FIELDS if f in schema_names]
        minimal_failing_extra_fields = _find_minimal_failing_set(collection, vector, available_extras)

        unsupported_seen = any(test.get("unsupported") for test in tests)
        if unsupported_seen:
            overall_status = "BLOCKED"

        report_items.append(
            {
                "collection": name,
                "stage": infer_stage_from_collection(name) or "unknown",
                "schema_fields": sorted(schema_names),
                "unsupported_seen": unsupported_seen,
                "minimal_failing_extra_fields": minimal_failing_extra_fields,
                "tests": tests,
            }
        )

    report = {
        "overall_status": overall_status,
        "collections": report_items,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_to_md(report), encoding="utf-8")

    print(f"output_fields_diag_json={out_json.resolve()}")
    print(f"output_fields_diag_md={out_md.resolve()}")
    print(f"overall_status={overall_status}")
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
