#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import platform
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pymilvus
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.milvus_service import get_milvus_service
from app.core.retrieval_branch_registry import get_qwen_collection


def _flatten_queries(golden: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper in golden.get("papers", []):
        paper_id = str(paper.get("paper_id") or "")
        for q in paper.get("queries", []):
            rows.append(
                {
                    "query": str(q.get("query") or ""),
                    "query_id": str(q.get("id") or ""),
                    "query_family": str(q.get("query_family") or "fact"),
                    "paper_ids": [paper_id] if paper_id else (q.get("expected_paper_ids") or []),
                }
            )

    for q in golden.get("cross_paper_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "compare"),
                "paper_ids": q.get("expected_papers") or q.get("paper_ids") or q.get("expected_paper_ids") or [],
            }
        )

    for q in golden.get("multimodal_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "table"),
                "paper_ids": q.get("paper_ids") or q.get("expected_papers") or [],
            }
        )

    return [row for row in rows if row["query"]]


def _sample_queries(rows: list[dict[str, Any]], per_family: int = 2, max_queries: int = 0) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("query_family") or "unknown")].append(row)

    picked: list[dict[str, Any]] = []
    for family in sorted(buckets.keys()):
        picked.extend(buckets[family][:per_family])
    if max_queries > 0:
        return picked[:max_queries]
    return picked


@contextlib.contextmanager
def _temp_env(values: dict[str, str]) -> Any:
    old: dict[str, str | None] = {}
    for key, value in values.items():
        old[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old_val in old.items():
            if old_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_val


def _build_expr_for_papers(paper_ids: list[str]) -> str:
    clean = [str(pid) for pid in paper_ids if str(pid)]
    if not clean:
        return "id >= 0"
    quoted_parts: list[str] = []
    for pid in clean:
        escaped = pid.replace("\\", "\\\\").replace('"', '\\"')
        quoted_parts.append(f'"{escaped}"')
    quoted = ", ".join(quoted_parts)
    return f"paper_id in [{quoted}]"


def _write_hydration_store(collection_name: str, paper_ids: list[str], output_path: Path, limit: int) -> dict[str, Any]:
    service = get_milvus_service()
    collection = service.get_collection(collection_name)
    expr = _build_expr_for_papers(paper_ids)
    try:
        rows = collection.query(
            expr=expr,
            output_fields=["id", "paper_id", "page_num", "content_type", "section", "content_data", "quality_score", "raw_data"],
            limit=max(limit, 100),
        )
    except Exception:
        rows = collection.query(
            expr=expr,
            output_fields=["id", "paper_id", "page_num", "content_type", "section", "content_data", "quality_score"],
            limit=max(limit, 100),
        )

    collection_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id")
        if row_id is None:
            continue
        raw_data = row.get("raw_data") if isinstance(row.get("raw_data"), dict) else {}
        key = str(row_id)
        collection_map[key] = {
            "source_chunk_id": str(raw_data.get("source_chunk_id") or row.get("source_chunk_id") or row_id),
            "paper_id": str(row.get("paper_id") or ""),
            "page_num": row.get("page_num"),
            "content_type": str(row.get("content_type") or "text"),
            "section": str(row.get("section") or ""),
            "content_data": str(row.get("content_data") or ""),
            "quality_score": row.get("quality_score"),
        }

    payload = {"collections": {collection_name: collection_map}}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "path": str(output_path),
        "collection": collection_name,
        "entry_count": len(collection_map),
        "expr": expr,
    }


async def _run_stage(
    stage: str,
    rows: list[dict[str, Any]],
    user_id: str,
    collection_name: str,
    *,
    id_only: bool,
    hydration_store_path: str,
) -> dict[str, Any]:
    settings.MILVUS_COLLECTION_CONTENTS_V2 = collection_name
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)

    detail: list[dict[str, Any]] = []
    errors: list[str] = []

    env_values = {
        "MILVUS_ID_ONLY_SEARCH": "1" if id_only else "0",
        "MILVUS_ENTITY_HYDRATION_STORE": hydration_store_path,
    }

    with _temp_env(env_values):
        for row in rows:
            try:
                result = await orchestrator.retrieve(
                    query=row["query"],
                    paper_ids=[str(pid) for pid in (row.get("paper_ids") or [])],
                    user_id=user_id,
                    top_k_per_subquestion=10,
                )
                meta = result.get("metadata") or {}
                diagnostics = meta.get("milvus_live_diagnostics") or {}
                detail.append(
                    {
                        "query_id": row.get("query_id"),
                        "query_family": row.get("query_family"),
                        "source_count": len(result.get("sources") or []),
                        "answer_mode": meta.get("answerMode"),
                        "citation_coverage": float(meta.get("citation_coverage") or 0.0),
                        "unsupported_claim_rate": float(meta.get("unsupported_claim_rate") or 0.0),
                        "answer_evidence_consistency": float(meta.get("answer_evidence_consistency") or 0.0),
                        "fallback_used": bool(diagnostics.get("fallback_used") or False),
                        "unsupported_field_type_count": int(diagnostics.get("unsupported_field_type_count") or 0),
                        "search_paths": diagnostics.get("search_paths") or [],
                        "output_fields_seen": diagnostics.get("output_fields_seen") or [],
                        "error": "",
                    }
                )
            except Exception as exc:
                msg = str(exc)
                errors.append(msg)
                detail.append(
                    {
                        "query_id": row.get("query_id"),
                        "query_family": row.get("query_family"),
                        "source_count": 0,
                        "answer_mode": "error",
                        "citation_coverage": 0.0,
                        "unsupported_claim_rate": 1.0,
                        "answer_evidence_consistency": 0.0,
                        "fallback_used": False,
                        "unsupported_field_type_count": 0,
                        "search_paths": [],
                        "output_fields_seen": [],
                        "error": msg,
                    }
                )

    unsupported_field_errors = sum(1 for item in detail if "unsupported field type" in (item.get("error") or "").lower())
    unsupported_count = sum(int(item.get("unsupported_field_type_count") or 0) for item in detail) + unsupported_field_errors
    fallback_used_count = sum(1 for item in detail if item.get("fallback_used"))

    return {
        "stage": stage,
        "collection": collection_name,
        "mode": "id_only" if id_only else "minimal_output_fields",
        "total_queries": len(detail),
        "successful_queries": sum(1 for item in detail if not item.get("error")),
        "unsupported_field_type_count": unsupported_count,
        "fallback_used_count": fallback_used_count,
        "citation_coverage_avg": sum(item["citation_coverage"] for item in detail) / max(len(detail), 1),
        "answer_evidence_consistency_avg": sum(item["answer_evidence_consistency"] for item in detail) / max(len(detail), 1),
        "details": detail,
        "errors": errors,
    }


def _first_index_params(collection: Collection) -> dict[str, Any]:
    indexes = list(getattr(collection, "indexes", []) or [])
    if not indexes:
        return {}
    params = getattr(indexes[0], "params", None)
    if isinstance(params, dict):
        return params
    return {}


def _connection_info(alias: str) -> dict[str, Any]:
    try:
        return connections.get_connection_addr(alias) or {}
    except Exception:
        return {}


def _collect_version_matrix(collection_name: str) -> dict[str, Any]:
    service = get_milvus_service()
    try:
        collection = service.get_collection(collection_name)
        index_params = _first_index_params(collection)
    except Exception:
        index_params = {}

    try:
        server_version = utility.get_server_version(using=service._alias)
    except Exception as exc:
        server_version = f"unknown ({exc})"

    try:
        import milvus_lite  # type: ignore

        milvus_lite_version = getattr(milvus_lite, "__version__", "unknown")
    except Exception:
        milvus_lite_version = "not-installed"

    conn = _connection_info(service._alias)
    uri = str(conn.get("uri") or "")
    embedded_active = uri.endswith(".db") or "milvus_lite" in uri.lower()

    return {
        "python_version": platform.python_version(),
        "pymilvus_version": getattr(pymilvus, "__version__", "unknown"),
        "milvus_server_version": server_version,
        "milvus_lite_version": milvus_lite_version,
        "index_type": index_params.get("index_type", "unknown"),
        "metric_type": index_params.get("metric_type", "unknown"),
        "embedded_fallback_enabled": os.getenv("MILVUS_EMBEDDED_FALLBACK", "true").lower() == "true",
        "embedded_fallback_active": embedded_active,
        "connection": conn,
        "collection": collection_name,
    }


def _create_minimal_clone_collection(source_collection_name: str, clone_collection_name: str, paper_ids: list[str], limit: int) -> dict[str, Any]:
    service = get_milvus_service()
    source = service.get_collection(source_collection_name)

    dim = service.inspect_collection_vector_dim(source, vector_field="embedding")

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="page_num", dtype=DataType.INT64),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]

    try:
        schema = CollectionSchema(fields=fields, description="v2.1.3 minimal clone", enable_dynamic_field=False)
    except TypeError:
        schema = CollectionSchema(fields=fields, description="v2.1.3 minimal clone")

    if utility.has_collection(clone_collection_name, using=service._alias):
        utility.drop_collection(clone_collection_name, using=service._alias)

    clone = Collection(name=clone_collection_name, schema=schema, using=service._alias)

    src_index = _first_index_params(source)
    index_params = {
        "metric_type": src_index.get("metric_type", "COSINE"),
        "index_type": src_index.get("index_type", "IVF_FLAT"),
        "params": src_index.get("params", {"nlist": 100}),
    }
    clone.create_index("embedding", index_params)

    expr = _build_expr_for_papers(paper_ids)
    rows = source.query(
        expr=expr,
        output_fields=["id", "user_id", "paper_id", "page_num", "content_type", "content_data", "embedding", "raw_data"],
        limit=max(limit, 100),
    )

    if rows:
        clone.insert(
            [
                {
                    "id": int(row.get("id")),
                    "user_id": str(row.get("user_id") or "benchmark-user"),
                    "source_chunk_id": str(
                        ((row.get("raw_data") or {}).get("source_chunk_id"))
                        if isinstance(row.get("raw_data"), dict)
                        else row.get("id")
                    ),
                    "paper_id": str(row.get("paper_id") or ""),
                    "page_num": int(row.get("page_num") or 0),
                    "content_type": str(row.get("content_type") or "text"),
                    "content_data": str(row.get("content_data") or ""),
                    "embedding": row.get("embedding") or [],
                }
                for row in rows
                if row.get("id") is not None and row.get("embedding")
            ]
        )
    clone.flush()
    clone.load()

    return {
        "source_collection": source_collection_name,
        "clone_collection": clone_collection_name,
        "rows_inserted": len(rows),
        "expr": expr,
        "index_params": index_params,
    }


def _to_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# v2.1.3 Milvus Live Search Entity Decode Report")
    lines.append("")
    lines.append(f"- overall_status: {report['overall_status']}")
    lines.append(f"- gate_passed_for_64x3: {report['gate_passed_for_64x3']}")
    lines.append(f"- sampled_queries: {report['sampled_queries']}")
    lines.append(f"- id_only_success: {report['id_only_success']}")
    lines.append("")

    lines.append("## ID-only live smoke")
    lines.append("")
    lines.append("| stage | collection | total | success | unsupported_field_type_count | fallback_used_count |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for item in report.get("id_only_stage_reports", []):
        lines.append(
            f"| {item['stage']} | {item['collection']} | {item['total_queries']} | {item['successful_queries']} | "
            f"{item['unsupported_field_type_count']} | {item['fallback_used_count']} |"
        )

    if report.get("minimal_clone"):
        lines.append("")
        lines.append("## Minimal clone diagnostics")
        lines.append("")
        lines.append("| stage | clone_collection | id_only_unsupported | id_only_fallback | minimal_fields_unsupported | minimal_fields_fallback |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for item in report.get("minimal_clone", {}).get("reports", []):
            lines.append(
                f"| {item['stage']} | {item['clone_collection']} | {item['id_only']['unsupported_field_type_count']} | "
                f"{item['id_only']['fallback_used_count']} | {item['minimal_output_fields']['unsupported_field_type_count']} | "
                f"{item['minimal_output_fields']['fallback_used_count']} |"
            )

    lines.append("")
    lines.append("## Version matrix")
    lines.append("")
    vm = report.get("version_matrix") or {}
    for key in [
        "python_version",
        "pymilvus_version",
        "milvus_server_version",
        "milvus_lite_version",
        "index_type",
        "metric_type",
        "embedded_fallback_enabled",
        "embedded_fallback_active",
    ]:
        lines.append(f"- {key}: {vm.get(key)}")

    lines.append("")
    lines.append("## Gate")
    lines.append("")
    lines.append("Only if all conditions are true, full 64x3 answer/citation can run:")
    lines.append(f"- Unsupported field type count = 0: {report['gate']['unsupported_zero']}")
    lines.append(f"- fallback_used = false: {report['gate']['fallback_false']}")
    lines.append(f"- answer_smoke total > 0: {report['gate']['answer_smoke_total_positive']}")
    lines.append("")
    return "\n".join(lines) + "\n"


async def main_async(args: argparse.Namespace) -> int:
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    rows = _flatten_queries(golden)
    sampled = _sample_queries(rows, per_family=args.per_family, max_queries=args.max_queries)
    sampled_paper_ids = sorted({str(pid) for row in sampled for pid in (row.get("paper_ids") or []) if str(pid)})

    id_only_stage_reports: list[dict[str, Any]] = []
    hydration_builds: list[dict[str, Any]] = []

    for stage in ["raw", "rule", "llm"]:
        collection_name = get_qwen_collection(stage)
        hydration_store = ROOT / "artifacts" / "benchmarks" / "v2_1_20" / f"v2_1_3_hydration_{stage}.json"
        hydration_builds.append(
            _write_hydration_store(
                collection_name=collection_name,
                paper_ids=sampled_paper_ids,
                output_path=hydration_store,
                limit=args.hydration_limit,
            )
        )
        id_only_stage_reports.append(
            await _run_stage(
                stage=stage,
                rows=sampled,
                user_id=args.user_id,
                collection_name=collection_name,
                id_only=True,
                hydration_store_path=str(hydration_store),
            )
        )

    id_only_success = all(
        item["unsupported_field_type_count"] == 0 and item["fallback_used_count"] == 0 and item["total_queries"] > 0
        for item in id_only_stage_reports
    )

    minimal_clone_section: dict[str, Any] | None = None
    if not id_only_success:
        clone_reports: list[dict[str, Any]] = []
        clone_builds: list[dict[str, Any]] = []
        for stage in ["raw", "rule", "llm"]:
            source_collection = get_qwen_collection(stage)
            clone_collection = f"{source_collection}_v2_1_3_minimal"
            clone_build = _create_minimal_clone_collection(
                source_collection_name=source_collection,
                clone_collection_name=clone_collection,
                paper_ids=sampled_paper_ids,
                limit=args.clone_limit,
            )
            clone_builds.append(clone_build)

            hydration_store = ROOT / "artifacts" / "benchmarks" / "v2_1_20" / f"v2_1_3_hydration_minimal_{stage}.json"
            _write_hydration_store(
                collection_name=clone_collection,
                paper_ids=sampled_paper_ids,
                output_path=hydration_store,
                limit=args.hydration_limit,
            )

            id_only_report = await _run_stage(
                stage=stage,
                rows=sampled,
                user_id=args.user_id,
                collection_name=clone_collection,
                id_only=True,
                hydration_store_path=str(hydration_store),
            )
            minimal_fields_report = await _run_stage(
                stage=stage,
                rows=sampled,
                user_id=args.user_id,
                collection_name=clone_collection,
                id_only=False,
                hydration_store_path=str(hydration_store),
            )
            clone_reports.append(
                {
                    "stage": stage,
                    "clone_collection": clone_collection,
                    "id_only": id_only_report,
                    "minimal_output_fields": minimal_fields_report,
                }
            )

        minimal_clone_section = {
            "builds": clone_builds,
            "reports": clone_reports,
        }

    version_matrix = _collect_version_matrix(get_qwen_collection("raw"))

    unsupported_total = sum(item["unsupported_field_type_count"] for item in id_only_stage_reports)
    fallback_total = sum(item["fallback_used_count"] for item in id_only_stage_reports)
    answer_smoke_total = sum(item["total_queries"] for item in id_only_stage_reports)

    gate = {
        "unsupported_zero": unsupported_total == 0,
        "fallback_false": fallback_total == 0,
        "answer_smoke_total_positive": answer_smoke_total > 0,
    }
    gate_passed_for_64x3 = all(gate.values())
    overall_status = "PASS" if gate_passed_for_64x3 else "BLOCKED"

    report = {
        "overall_status": overall_status,
        "gate_passed_for_64x3": gate_passed_for_64x3,
        "sampled_queries": len(sampled),
        "sampled_paper_ids": sampled_paper_ids,
        "id_only_success": id_only_success,
        "hydration_builds": hydration_builds,
        "id_only_stage_reports": id_only_stage_reports,
        "minimal_clone": minimal_clone_section,
        "version_matrix": version_matrix,
        "gate": gate,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_report = Path(args.report_md)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = _to_md(report)
    out_md.write_text(md, encoding="utf-8")
    out_report.write_text(md, encoding="utf-8")

    print(f"v2_1_3_json={out_json}")
    print(f"v2_1_3_md={out_md}")
    print(f"v2_1_3_report={out_report}")
    print(f"overall_status={overall_status}")
    print(f"gate_passed_for_64x3={gate_passed_for_64x3}")
    return 0 if gate_passed_for_64x3 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2.1.3 Milvus entity decode smoke")
    parser.add_argument(
        "--golden",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "golden_queries_acceptance_v2_1.json"),
    )
    parser.add_argument(
        "--output-json",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "v2_1_3_entity_decode_report.json"),
    )
    parser.add_argument(
        "--output-md",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "v2_1_3_entity_decode_report.md"),
    )
    parser.add_argument(
        "--report-md",
        default=str(ROOT / "v2_1_3_entity_decode_report.md"),
    )
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument("--per-family", type=int, default=2)
    parser.add_argument("--max-queries", type=int, default=0)
    parser.add_argument("--hydration-limit", type=int, default=5000)
    parser.add_argument("--clone-limit", type=int, default=5000)
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
