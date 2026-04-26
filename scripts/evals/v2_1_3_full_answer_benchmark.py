#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import platform
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pymilvus
from pymilvus import utility

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings, normalize_embedding_model_name
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.milvus_service import get_milvus_service
from app.core.retrieval_branch_registry import get_qwen_collection


CITATION_PATTERN = re.compile(r"\[([^\[\],]+),\s*([^\[\]]+)\]")


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(int(len(values) * 0.95) - 1, 0)
    return float(values[index])


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
                    "expected_evidence_type": q.get("expected_evidence_type") or [],
                }
            )

    for q in golden.get("cross_paper_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "compare"),
                "paper_ids": q.get("expected_papers") or q.get("paper_ids") or q.get("expected_paper_ids") or [],
                "expected_evidence_type": q.get("expected_evidence_type") or [],
            }
        )

    for q in golden.get("multimodal_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "table"),
                "paper_ids": q.get("paper_ids") or q.get("expected_papers") or [],
                "expected_evidence_type": q.get("expected_evidence_type") or [],
            }
        )
    return [row for row in rows if row["query"]]


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
    capped_limit = min(max(limit, 2000), 16000)
    try:
        rows = collection.query(
            expr=expr,
            output_fields=["id", "paper_id", "page_num", "content_type", "section", "content_data", "quality_score", "raw_data"],
            limit=capped_limit,
        )
    except Exception:
        rows = collection.query(
            expr=expr,
            output_fields=["id", "paper_id", "page_num", "content_type", "section", "content_data", "quality_score"],
            limit=capped_limit,
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


def _citation_jump_validity(answer: str, sources: list[dict[str, Any]]) -> float:
    citations = CITATION_PATTERN.findall(answer or "")
    if not citations:
        return 0.0
    valid_set = set()
    for source in sources:
        paper = str(source.get("paper_title") or source.get("paper_id") or "").strip()
        section = str(source.get("section") or source.get("section_path") or source.get("page_num") or "").strip()
        if paper and section:
            valid_set.add((paper[:30], section))
    hit = 0
    for paper, section in citations:
        if (paper.strip()[:30], section.strip()) in valid_set:
            hit += 1
    return hit / max(len(citations), 1)


def _table_figure_grounding_validity(expected_types: list[str], sources: list[dict[str, Any]]) -> tuple[float, float]:
    source_types = [str(item.get("content_type") or "").lower() for item in sources]
    has_table = any(t == "table" for t in source_types)
    has_figure = any(t == "figure" for t in source_types)
    expected_lower = [t.lower() for t in expected_types]
    table_expected = "table" in expected_lower
    figure_expected = "figure" in expected_lower
    table_valid = 1.0 if (not table_expected or has_table) else 0.0
    figure_valid = 1.0 if (not figure_expected or has_figure) else 0.0
    return table_valid, figure_valid


def _failure_type(detail: dict[str, Any]) -> str:
    if detail["source_count"] == 0:
        return "retrieval_miss"
    if detail["unsupported_field_type_count"] > 0:
        return "unsupported_field_type"
    if detail["fallback_used"]:
        return "fallback_used"
    if detail["answer_mode"] == "abstain" and detail["expected_should_answer"]:
        return "abstain_wrong"
    if detail["unsupported_claim_rate"] > 0.5:
        return "unsupported_claim"
    if detail["citation_coverage"] < 0.3:
        return "citation_wrong"
    if detail["answer_evidence_consistency"] < 0.35:
        return "answer_hallucination"
    if detail["expected_table"] and not detail["table_grounding_valid"]:
        return "evidence_type_wrong"
    if detail["expected_figure"] and not detail["figure_grounding_valid"]:
        return "evidence_type_wrong"
    return ""


def _collect_version_matrix(collection_name: str) -> dict[str, Any]:
    service = get_milvus_service()
    try:
        collection = service.get_collection(collection_name)
        indexes = list(getattr(collection, "indexes", []) or [])
        index_params = getattr(indexes[0], "params", {}) if indexes else {}
        if not isinstance(index_params, dict):
            index_params = {}
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

    try:
        conn = utility.connections.get_connection_addr(service._alias)  # type: ignore[attr-defined]
    except Exception:
        conn = {}

    uri = str((conn or {}).get("uri") or "")
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
    }


async def _run_stage_full(
    *,
    stage: str,
    collection_name: str,
    rows: list[dict[str, Any]],
    user_id: str,
    hydration_store_path: str,
    output_path: Path,
) -> dict[str, Any]:
    settings.MILVUS_COLLECTION_CONTENTS_V2 = collection_name
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)

    details: list[dict[str, Any]] = []
    latency_values: list[float] = []

    with _temp_env(
        {
            "MILVUS_ID_ONLY_SEARCH": "1",
            "MILVUS_ENTITY_HYDRATION_STORE": hydration_store_path,
            "MILVUS_FORCE_QUERY_FALLBACK": "0",
        }
    ):
        for row in rows:
            query_text = str(row.get("query") or "")
            expected_types = [str(t) for t in (row.get("expected_evidence_type") or [])]
            paper_ids = [str(pid) for pid in (row.get("paper_ids") or []) if str(pid)]

            t0 = time.perf_counter()
            result = await orchestrator.retrieve(
                query=query_text,
                paper_ids=paper_ids,
                user_id=user_id,
                top_k_per_subquestion=10,
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0
            latency_values.append(latency_ms)

            metadata = result.get("metadata") or {}
            diagnostics = metadata.get("milvus_live_diagnostics") or {}
            sources = result.get("sources") or []

            table_valid, figure_valid = _table_figure_grounding_validity(expected_types, sources)
            detail = {
                "query_id": str(row.get("query_id") or ""),
                "query_family": str(row.get("query_family") or "unknown"),
                "answer_mode": str(metadata.get("answerMode") or "unknown"),
                "citation_coverage": float(metadata.get("citation_coverage") or 0.0),
                "unsupported_claim_rate": float(metadata.get("unsupported_claim_rate") or 0.0),
                "answer_evidence_consistency": float(metadata.get("answer_evidence_consistency") or 0.0),
                "table_grounding_valid": bool(table_valid),
                "figure_grounding_valid": bool(figure_valid),
                "citation_jump_validity": _citation_jump_validity(str(result.get("answer") or ""), sources),
                "latency_ms": latency_ms,
                "source_count": len(sources),
                "expected_table": "table" in [t.lower() for t in expected_types],
                "expected_figure": "figure" in [t.lower() for t in expected_types],
                "expected_should_answer": True,
                "fallback_used": bool(diagnostics.get("fallback_used") or False),
                "unsupported_field_type_count": int(diagnostics.get("unsupported_field_type_count") or 0),
                "search_paths": diagnostics.get("search_paths") or [],
                "output_fields_seen": diagnostics.get("output_fields_seen") or [],
            }
            detail["failure_type"] = _failure_type(detail)
            details.append(detail)

    by_family: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "citation_coverage": [],
            "unsupported_claim_rate": [],
            "answer_evidence_consistency": [],
            "citation_jump_validity": [],
            "latency_ms": [],
        }
    )
    for item in details:
        bucket = by_family[item["query_family"]]
        bucket["count"] += 1
        bucket["citation_coverage"].append(item["citation_coverage"])
        bucket["unsupported_claim_rate"].append(item["unsupported_claim_rate"])
        bucket["answer_evidence_consistency"].append(item["answer_evidence_consistency"])
        bucket["citation_jump_validity"].append(item["citation_jump_validity"])
        bucket["latency_ms"].append(item["latency_ms"])

    mode_dist = Counter(item["answer_mode"] for item in details)
    failure_dist = Counter(item["failure_type"] for item in details if item["failure_type"])

    report = {
        "stage": stage,
        "collection": collection_name,
        "id_only_mode": True,
        "hydration_store": hydration_store_path,
        "total_queries": len(details),
        "citation_coverage_avg": sum(item["citation_coverage"] for item in details) / max(len(details), 1),
        "unsupported_claim_rate_avg": sum(item["unsupported_claim_rate"] for item in details) / max(len(details), 1),
        "answer_evidence_consistency_avg": sum(item["answer_evidence_consistency"] for item in details)
        / max(len(details), 1),
        "table_grounding_validity": sum(1.0 if item["table_grounding_valid"] else 0.0 for item in details)
        / max(len(details), 1),
        "figure_grounding_validity": sum(1.0 if item["figure_grounding_valid"] else 0.0 for item in details)
        / max(len(details), 1),
        "citation_jump_validity": sum(item["citation_jump_validity"] for item in details) / max(len(details), 1),
        "answer_latency_p50_ms": _p50(latency_values),
        "answer_latency_p95_ms": _p95(latency_values),
        "answer_mode_distribution": dict(mode_dist),
        "failure_types": dict(failure_dist),
        "fallback_used_count": sum(1 for item in details if item["fallback_used"]),
        "unsupported_field_type_count": sum(int(item["unsupported_field_type_count"] or 0) for item in details),
        "by_query_family": {
            family: {
                "count": values["count"],
                "citation_coverage_avg": sum(values["citation_coverage"]) / max(values["count"], 1),
                "unsupported_claim_rate_avg": sum(values["unsupported_claim_rate"]) / max(values["count"], 1),
                "answer_evidence_consistency_avg": sum(values["answer_evidence_consistency"]) / max(values["count"], 1),
                "citation_jump_validity_avg": sum(values["citation_jump_validity"]) / max(values["count"], 1),
                "latency_p50_ms": _p50(values["latency_ms"]),
                "latency_p95_ms": _p95(values["latency_ms"]),
            }
            for family, values in by_family.items()
        },
        "query_details": details,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _build_verdict(stage_reports: dict[str, dict[str, Any]]) -> tuple[str, bool, dict[str, bool]]:
    unsupported_ok = all((item.get("unsupported_field_type_count") or 0) == 0 for item in stage_reports.values())
    fallback_ok = all((item.get("fallback_used_count") or 0) == 0 for item in stage_reports.values())
    total_ok = all((item.get("total_queries") or 0) > 0 for item in stage_reports.values())

    hard_gate = {
        "unsupported_zero": unsupported_ok,
        "fallback_false": fallback_ok,
        "answer_total_positive": total_ok,
    }
    hard_pass = all(hard_gate.values())
    if not hard_pass:
        return "BLOCKED", False, hard_gate

    quality_ok = all(
        (item.get("citation_coverage_avg") or 0.0) >= 0.30
        and (item.get("answer_evidence_consistency_avg") or 0.0) >= 0.35
        for item in stage_reports.values()
    )
    if quality_ok:
        return "PASS", True, hard_gate
    return "CONDITIONAL", False, hard_gate


def _default_strategy(stage_reports: dict[str, dict[str, Any]]) -> dict[str, str]:
    best_stage = max(
        stage_reports.keys(),
        key=lambda s: (
            float(stage_reports[s].get("answer_evidence_consistency_avg") or 0.0),
            float(stage_reports[s].get("citation_coverage_avg") or 0.0),
        ),
    )
    return {
        "recommended_default_stage": best_stage,
        "raw": "高精度证据定位与可解释审计优先，适合保守问答。",
        "rule": "规则增强检索，作为生产默认优先策略。",
        "llm": "语义扩展与复杂表达覆盖，作为补充策略。",
    }


def _write_full_report(
    *,
    report_path: Path,
    verdict: str,
    can_expand_50: bool,
    stage_reports: dict[str, dict[str, Any]],
    gate: dict[str, bool],
    version_matrix: dict[str, Any],
    strategy: dict[str, str],
) -> None:
    lines: list[str] = []
    lines.append("# v2.1.3 Full Answer/Citation Acceptance Report")
    lines.append("")
    lines.append(f"- verdict: {verdict}")
    lines.append(f"- can_expand_to_50_papers: {can_expand_50}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    lines.append(f"- Unsupported field type count = 0: {gate['unsupported_zero']}")
    lines.append(f"- fallback_used = false: {gate['fallback_false']}")
    lines.append(f"- answer_smoke total > 0: {gate['answer_total_positive']}")
    lines.append("")
    lines.append("## Stage Summary")
    lines.append("")
    lines.append("| stage | total | citation_coverage_avg | consistency_avg | unsupported_field_type_count | fallback_used_count |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for stage in ["raw", "rule", "llm"]:
        item = stage_reports[stage]
        lines.append(
            f"| {stage} | {item['total_queries']} | {item['citation_coverage_avg']:.4f} | {item['answer_evidence_consistency_avg']:.4f} | "
            f"{item['unsupported_field_type_count']} | {item['fallback_used_count']} |"
        )
    lines.append("")
    lines.append("## Default Strategy")
    lines.append("")
    lines.append(f"- recommended_default_stage: {strategy['recommended_default_stage']}")
    lines.append(f"- raw: {strategy['raw']}")
    lines.append(f"- rule: {strategy['rule']}")
    lines.append(f"- llm: {strategy['llm']}")
    lines.append("")
    lines.append("## Version Matrix")
    lines.append("")
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
        lines.append(f"- {key}: {version_matrix.get(key)}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(args: argparse.Namespace) -> int:
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    rows = _flatten_queries(golden)
    if args.max_queries > 0:
        rows = rows[: args.max_queries]

    if not rows:
        print("BLOCKED: no queries selected for full acceptance")
        return 1

    embedding_model = normalize_embedding_model_name(settings.EMBEDDING_MODEL)
    if embedding_model != "qwen3-vl-2b":
        print(f"BLOCKED: branch=qwen model={settings.EMBEDDING_MODEL}")
        return 1

    if settings.SCIENTIFIC_TEXT_BRANCH_ENABLED:
        print("BLOCKED: specter2_enabled=true but no dedicated specter2 collection")
        return 1

    all_paper_ids = sorted({str(pid) for row in rows for pid in (row.get("paper_ids") or []) if str(pid)})

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_reports: dict[str, dict[str, Any]] = {}

    service = get_milvus_service()

    for stage in ["raw", "rule", "llm"]:
        collection_name = get_qwen_collection(stage)
        collection_dim = service.inspect_collection_vector_dim(
            service.get_collection(collection_name),
            vector_field="embedding",
        )

        startup_payload = {
            "benchmark": "v2.1.3-qwen-full-acceptance",
            "stage": stage,
            "branch": "qwen",
            "embedding_model": "qwen",
            "collection": collection_name,
            "query_dim": args.query_dim,
            "collection_dim": collection_dim,
            "specter2_enabled": False,
            "bge_m3_enabled": False,
            "id_only_enabled": True,
            "hydration_enabled": True,
        }
        print(json.dumps(startup_payload, ensure_ascii=False))

        if args.query_dim != collection_dim:
            print(f"BLOCKED: query_dim={args.query_dim} collection_dim={collection_dim}")
            return 1

        hydration_store = out_dir / f"v2_1_3_hydration_full_{stage}.json"
        _write_hydration_store(
            collection_name=collection_name,
            paper_ids=all_paper_ids,
            output_path=hydration_store,
            limit=args.hydration_limit,
        )

        output_path = out_dir / f"answer_{stage}_v2_1_3{args.output_suffix}.json"
        stage_reports[stage] = await _run_stage_full(
            stage=stage,
            collection_name=collection_name,
            rows=rows,
            user_id=args.user_id,
            hydration_store_path=str(hydration_store),
            output_path=output_path,
        )

        if (stage_reports[stage].get("fallback_used_count") or 0) > 0:
            print("BLOCKED: fallback_used=true")
            return 1

        if (stage_reports[stage].get("unsupported_field_type_count") or 0) > 0:
            print("BLOCKED: unsupported_field_type_count>0")
            return 1

    comparison = {
        "version": "v2.1.3",
        "id_only_mode": True,
        "stages": stage_reports,
    }
    comparison_path = out_dir / f"answer_comparison_v2_1_3{args.output_suffix}.json"
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")

    version_matrix = _collect_version_matrix(get_qwen_collection("raw"))
    verdict, can_expand_50, gate = _build_verdict(stage_reports)
    strategy = _default_strategy(stage_reports)

    report_path = out_dir / args.report_name
    _write_full_report(
        report_path=report_path,
        verdict=verdict,
        can_expand_50=can_expand_50,
        stage_reports=stage_reports,
        gate=gate,
        version_matrix=version_matrix,
        strategy=strategy,
    )

    print(f"answer_raw={out_dir / f'answer_raw_v2_1_3{args.output_suffix}.json'}")
    print(f"answer_rule={out_dir / f'answer_rule_v2_1_3{args.output_suffix}.json'}")
    print(f"answer_llm={out_dir / f'answer_llm_v2_1_3{args.output_suffix}.json'}")
    print(f"answer_comparison={comparison_path}")
    print(f"full_report={report_path}")
    print(f"verdict={verdict}")
    print(f"can_expand_to_50={can_expand_50}")

    return 0 if verdict in {"PASS", "CONDITIONAL"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2.1.3 full 64x3 answer/citation benchmark")
    parser.add_argument(
        "--golden",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "golden_queries_acceptance_v2_1.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20"),
    )
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument("--hydration-limit", type=int, default=50000)
    parser.add_argument("--max-queries", type=int, default=64)
    parser.add_argument("--query-dim", type=int, default=2048)
    parser.add_argument("--output-suffix", default="_qwen")
    parser.add_argument("--report-name", default="v2_1_3_qwen_full_acceptance_report.md")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
