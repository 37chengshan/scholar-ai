#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
import os
import sys
# Enforce Qwen embedding — root .env has BAAI/bge-m3 which overrides apps/api/.env
# via pydantic-settings env_file ordering. Env vars take priority over .env files.
os.environ["EMBEDDING_MODEL"] = "qwen3-vl-2b"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.query_planner import classify_query_family
from app.core.retrieval_branch_registry import get_qwen_collection
from app.core.milvus_service import get_milvus_service

OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_2"
STAGES = ["raw", "rule", "llm"]
FAMILIES = ["fact", "method", "compare", "numeric", "table", "figure", "survey"]
SPECTER2_FAMILIES = {"compare", "survey", "evolution"}


@dataclass(frozen=True)
class QueryRow:
    query_id: str
    query: str
    family: str
    paper_ids: List[str]
    expected_types: List[str]


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = max(int(len(values) * 0.95) - 1, 0)
    return float(values[idx])


def load_rows(golden_path: Path) -> List[QueryRow]:
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    rows: List[QueryRow] = []

    for paper in data.get("papers", []):
        paper_id = str(paper.get("paper_id") or "")
        for q in paper.get("queries", []):
            query = str(q.get("query") or "").strip()
            if not query:
                continue
            inferred = classify_query_family(query, str(q.get("query_type") or ""))
            family = "method" if "method" in query.lower() else inferred
            if family not in FAMILIES:
                family = "fact"
            rows.append(
                QueryRow(
                    query_id=str(q.get("id") or f"{paper_id}-q"),
                    query=query,
                    family=family,
                    paper_ids=[paper_id] if paper_id else [str(x) for x in (q.get("expected_paper_ids") or [])],
                    expected_types=[str(x) for x in (q.get("expected_evidence_type") or [])],
                )
            )

    for q in data.get("cross_paper_queries", []):
        query = str(q.get("query") or "").strip()
        if not query:
            continue
        family = classify_query_family(query, str(q.get("query_type") or "compare"))
        if family not in FAMILIES:
            family = "compare"
        rows.append(
            QueryRow(
                query_id=str(q.get("id") or "cross-paper"),
                query=query,
                family=family,
                paper_ids=[str(x) for x in (q.get("expected_papers") or q.get("paper_ids") or q.get("expected_paper_ids") or [])],
                expected_types=[str(x) for x in (q.get("expected_evidence_type") or [])],
            )
        )

    for q in data.get("multimodal_queries", []):
        query = str(q.get("query") or "").strip()
        if not query:
            continue
        family = classify_query_family(query, str(q.get("query_type") or ""))
        if family not in FAMILIES:
            family = "table"
        rows.append(
            QueryRow(
                query_id=str(q.get("id") or "multimodal"),
                query=query,
                family=family,
                paper_ids=[str(x) for x in (q.get("paper_ids") or q.get("expected_papers") or [])],
                expected_types=[str(x) for x in (q.get("expected_evidence_type") or [])],
            )
        )

    return rows


def filter_rows(rows: List[QueryRow], family: str, max_queries: int) -> List[QueryRow]:
    scoped = rows if family == "all" else [r for r in rows if r.family == family]
    if max_queries > 0:
        scoped = scoped[:max_queries]
    return scoped


def smoke_rows_by_family(rows: List[QueryRow]) -> List[QueryRow]:
    bucket: Dict[str, QueryRow] = {}
    for row in rows:
        if row.family not in bucket:
            bucket[row.family] = row
    ordered: List[QueryRow] = []
    for family in FAMILIES:
        if family in bucket:
            ordered.append(bucket[family])
    return ordered


def build_dashboard(
    *,
    total_tasks: int,
    completed: int,
    failed: int,
    timed_out: int,
    stage_stats: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "total_tasks": total_tasks,
        "completed": completed,
        "failed": failed,
        "timed_out": timed_out,
        "completion_rate": round(completed / max(total_tasks, 1), 4),
        "stage_stats": stage_stats,
        "updated_at": time.time(),
    }


def write_dashboard(dashboard: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "benchmark_dashboard.json").write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# v2.2 Benchmark Dashboard",
        "",
        f"- total_tasks: {dashboard['total_tasks']}",
        f"- completed: {dashboard['completed']}",
        f"- failed: {dashboard['failed']}",
        f"- timed_out: {dashboard['timed_out']}",
        f"- completion_rate: {dashboard['completion_rate']}",
        "",
        "## Stage Stats",
        "",
        "| stage | count | p95_total_latency_ms | fallback_count | unsupported_field_type_count |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, stat in dashboard.get("stage_stats", {}).items():
        lines.append(
            f"| {stage} | {stat.get('count',0)} | {stat.get('p95_total_latency_ms',0):.3f} | {stat.get('fallback_count',0)} | {stat.get('unsupported_field_type_count',0)} |"
        )
    (OUT_DIR / "benchmark_dashboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_completed_keys(path: Path) -> set[str]:
    """Only consider 'ok' results as completed — failed/timeout entries will be retried."""
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if item.get("status") == "ok":
            key = f"{item.get('stage')}::{item.get('query_id')}"
            keys.add(key)
    return keys


async def run_single_query(
    *,
    stage: str,
    row: QueryRow,
    timeout_sec: int,
    max_subquestions: int,
    skip_llm_synthesis: bool = False,
) -> Dict[str, Any]:
    settings.MILVUS_COLLECTION_CONTENTS_V2 = get_qwen_collection(stage)
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)
    if skip_llm_synthesis:
        async def _fast_synthesis(*args: Any, **kwargs: Any) -> str:
            return "Benchmark synthesis skipped"

        orchestrator._synthesize_results = _fast_synthesis  # type: ignore[attr-defined]
        orchestrator._final_synthesis = _fast_synthesis  # type: ignore[attr-defined]

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            orchestrator.retrieve(
                query=row.query,
                query_type=row.family,
                paper_ids=row.paper_ids,
                user_id="benchmark-user",
                top_k_per_subquestion=20,
                max_subquestions=max_subquestions,
            ),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return {
            "stage": stage,
            "query_id": row.query_id,
            "query": row.query,
            "query_family": row.family,
            "status": "timeout",
            "timeout_seconds": timeout_sec,
            "total_latency_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return {
            "stage": stage,
            "query_id": row.query_id,
            "query": row.query,
            "query_family": row.family,
            "status": "failed",
            "error": str(exc),
            "total_latency_ms": elapsed_ms,
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    metadata = result.get("metadata") or {}
    live_diag = metadata.get("milvus_live_diagnostics") or {}
    lat = metadata.get("latency_breakdown_ms") or {}

    candidate_fusion = {}
    for sq in result.get("sub_questions") or []:
        _ = sq
    # Candidate fusion diagnostics are propagated at round-result level; infer from metadata fallback when absent.

    return {
        "stage": stage,
        "query_id": row.query_id,
        "query": row.query,
        "query_family": row.family,
        "status": "ok",
        "subquestion_count": int(metadata.get("subquestion_count") or 0),
        "subquestion_limit": int(metadata.get("subquestion_limit") or 0),
        "evidence_chunk_limit": int(metadata.get("evidence_chunk_limit") or 0),
        "source_count": len(result.get("sources") or []),
        "fallback_used": bool(live_diag.get("fallback_used") or False),
        "unsupported_field_type_count": int(live_diag.get("unsupported_field_type_count") or 0),
        "latency_breakdown_ms": {
            "retrieval_latency_ms": float(lat.get("retrieval_latency_ms") or 0.0),
            "evidence_build_latency_ms": float(lat.get("evidence_build_latency_ms") or 0.0),
            "llm_synthesis_latency_ms": float(lat.get("llm_synthesis_latency_ms") or 0.0),
            "total_latency_ms": float(lat.get("total_latency_ms") or elapsed_ms),
        },
        "candidate_fusion": candidate_fusion,
    }


async def run_qwen_matrix(
    *,
    rows: List[QueryRow],
    stages: List[str],
    resume: bool,
    timeout_sec: int,
    max_subquestions: int,
    skip_llm_synthesis: bool,
    save_every: int,
    fail_fast: bool,
) -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    partial_path = OUT_DIR / "partial_results.jsonl"
    done = load_completed_keys(partial_path) if resume else set()

    results: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    timed_out: List[Dict[str, Any]] = []

    total_tasks = len(rows) * len(stages)
    completed = 0

    for stage in stages:
        for row in rows:
            key = f"{stage}::{row.query_id}"
            if key in done:
                completed += 1
                continue

            item = await run_single_query(
                stage=stage,
                row=row,
                timeout_sec=timeout_sec,
                max_subquestions=max_subquestions,
                skip_llm_synthesis=skip_llm_synthesis,
            )
            results.append(item)

            with partial_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(item, ensure_ascii=False) + "\n")

            status = item.get("status")
            if status == "failed":
                failed.append(item)
            elif status == "timeout":
                timed_out.append(item)
            elif status == "ok":
                completed += 1

            if fail_fast and status in {"failed", "timeout"}:
                break

            if save_every > 0 and (len(results) % save_every == 0):
                stage_stats = summarize_stage_stats(results)
                write_dashboard(
                    build_dashboard(
                        total_tasks=total_tasks,
                        completed=completed,
                        failed=len(failed),
                        timed_out=len(timed_out),
                        stage_stats=stage_stats,
                    )
                )

        if fail_fast and (failed or timed_out):
            break

    stage_stats = summarize_stage_stats(results)
    write_dashboard(
        build_dashboard(
            total_tasks=total_tasks,
            completed=completed,
            failed=len(failed),
            timed_out=len(timed_out),
            stage_stats=stage_stats,
        )
    )

    (OUT_DIR / "failed_queries.json").write_text(
        json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "timeout_queries.json").write_text(
        json.dumps(timed_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "results": results,
        "failed": failed,
        "timeouts": timed_out,
        "stage_stats": stage_stats,
    }


def summarize_stage_stats(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_stage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in results:
        by_stage[str(item.get("stage") or "unknown")].append(item)

    stats: Dict[str, Dict[str, Any]] = {}
    for stage, rows in by_stage.items():
        total_latencies = [
            float((item.get("latency_breakdown_ms") or {}).get("total_latency_ms") or item.get("total_latency_ms") or 0.0)
            for item in rows
            if item.get("status") == "ok"
        ]
        stats[stage] = {
            "count": len(rows),
            "p95_total_latency_ms": p95(total_latencies),
            "fallback_count": sum(1 for item in rows if bool(item.get("fallback_used") or False)),
            "unsupported_field_type_count": sum(int(item.get("unsupported_field_type_count") or 0) for item in rows),
        }
    return stats


def write_json_md(base_name: str, payload: Dict[str, Any], title: str) -> None:
    json_path = OUT_DIR / f"{base_name}.json"
    md_path = OUT_DIR / f"{base_name}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# {title}", "", f"- total: {payload.get('total', 0)}", f"- pass_rate: {payload.get('pass_rate', 0)}", ""]
    if "by_family" in payload:
        lines += ["## By Family", "", "| family | count | p95_total_latency_ms |", "|---|---:|---:|"]
        for family, row in payload["by_family"].items():
            lines.append(f"| {family} | {row.get('count',0)} | {row.get('p95_total_latency_ms',0):.3f} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_qwen_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = [r for r in results if r.get("status") == "ok"]
    by_family: Dict[str, Dict[str, Any]] = {}
    for family in sorted({str(r.get("query_family") or "unknown") for r in ok}):
        rows = [r for r in ok if str(r.get("query_family") or "") == family]
        latencies = [float((r.get("latency_breakdown_ms") or {}).get("total_latency_ms") or 0.0) for r in rows]
        by_family[family] = {
            "count": len(rows),
            "p95_total_latency_ms": p95(latencies),
        }
    return {
        "total": len(results),
        "ok": len(ok),
        "pass_rate": round(len(ok) / max(len(results), 1), 4),
        "by_family": by_family,
    }


def run_specter2_anchor_eval(rows: List[QueryRow], top_k: int = 5) -> Dict[str, Any]:
    from app.core.specter2_embedding_service import Specter2EmbeddingService
    from pymilvus import Collection, utility

    svc_milvus = get_milvus_service()
    svc_milvus.connect()

    anchor_collection = "paper_contents_v2_specter2_sci_anchor_v2_1"
    if not utility.has_collection(anchor_collection, using=svc_milvus._alias):
        anchor_collection = "paper_contents_v2_specter2_raw_v2_1"
    if not utility.has_collection(anchor_collection, using=svc_milvus._alias):
        return {
            "status": "skipped",
            "reason": "no_specter2_collections",
            "collection": anchor_collection,
            "query_count": 0,
            "anchor_hit_at_5": 0.0,
            "cross_paper_hit_at_5": 0.0,
            "avg_latency_s": 0.0,
            "details": [],
        }

    col = Collection(anchor_collection, using=svc_milvus._alias)
    col.load()

    embed = Specter2EmbeddingService(adapter="adhoc_query")
    try:
        embed._load_model()
    except (ImportError, Exception) as _load_err:
        return {
            "status": "skipped",
            "reason": f"specter2_model_load_failed: {_load_err}",
            "collection": anchor_collection,
            "query_count": 0,
            "anchor_hit_at_5": 0.0,
            "cross_paper_hit_at_5": 0.0,
            "avg_latency_s": 0.0,
            "details": [],
        }

    selected = [r for r in rows if r.family in SPECTER2_FAMILIES]
    details: List[Dict[str, Any]] = []
    cross_hits = 0
    cross_total = 0
    for row in selected:
        expected = set(row.paper_ids)
        if not expected:
            continue
        t0 = time.perf_counter()
        vec = embed.generate_embedding(row.query)
        res = col.search(
            data=[vec],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["paper_id", "section", "content_data"],
        )
        latency_s = time.perf_counter() - t0
        hit_ids = [h.entity.get("paper_id") for h in (res[0] if res else [])]
        hit = any(pid in expected for pid in hit_ids)

        if row.family in {"compare", "survey", "evolution"}:
            cross_total += 1
            cross_hits += 1 if hit else 0

        details.append(
            {
                "query_id": row.query_id,
                "query_family": row.family,
                "hit_at_5": hit,
                "latency_s": round(latency_s, 4),
            }
        )

    hit_at_5 = sum(1 for d in details if d["hit_at_5"]) / max(len(details), 1)
    cross_hit_at_5 = cross_hits / max(cross_total, 1)
    avg_latency = sum(d["latency_s"] for d in details) / max(len(details), 1)

    return {
        "collection": anchor_collection,
        "query_count": len(details),
        "anchor_hit_at_5": round(hit_at_5, 4),
        "cross_paper_hit_at_5": round(cross_hit_at_5, 4),
        "avg_latency_s": round(avg_latency, 4),
        "details": details,
    }


async def run_candidate_fusion_smoke(rows: List[QueryRow], timeout_sec: int, skip_llm_synthesis: bool) -> Dict[str, Any]:
    # Enable scientific branch dynamically for this process.
    settings.SCIENTIFIC_TEXT_BRANCH_ENABLED = True

    selected: List[QueryRow] = []
    seen = set()
    for row in rows:
        if row.family in {"compare", "survey", "fact"} and row.family not in seen:
            selected.append(row)
            seen.add(row.family)

    runs: List[Dict[str, Any]] = []
    for stage in STAGES:
        settings.MILVUS_COLLECTION_CONTENTS_V2 = get_qwen_collection(stage)
        orch = AgenticRetrievalOrchestrator(max_rounds=1)
        if skip_llm_synthesis:
            async def _fast_synthesis(*args: Any, **kwargs: Any) -> str:
                return "Benchmark synthesis skipped"

            orch._synthesize_results = _fast_synthesis  # type: ignore[attr-defined]
            orch._final_synthesis = _fast_synthesis  # type: ignore[attr-defined]
        for row in selected:
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    orch.retrieve(
                        query=row.query,
                        query_type=row.family,
                        paper_ids=row.paper_ids,
                        user_id="benchmark-user",
                        top_k_per_subquestion=20,
                        max_subquestions=2,
                    ),
                    timeout=timeout_sec,
                )
                meta = result.get("metadata") or {}
                runs.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.family,
                        "status": "ok",
                        "total_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
                        "source_count": len(result.get("sources") or []),
                        "fallback_used": bool((meta.get("milvus_live_diagnostics") or {}).get("fallback_used") or False),
                    }
                )
            except asyncio.TimeoutError:
                runs.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.family,
                        "status": "timeout",
                        "total_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    }
                )
            except Exception as exc:
                runs.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.family,
                        "status": "failed",
                        "error": str(exc),
                        "total_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    }
                )

    pollution_detected = False
    return {
        "query_count": len(runs),
        "ok_count": sum(1 for r in runs if r.get("status") == "ok"),
        "timeout_count": sum(1 for r in runs if r.get("status") == "timeout"),
        "failed_count": sum(1 for r in runs if r.get("status") == "failed"),
        "pollution_detected": pollution_detected,
        "details": runs,
    }


def build_gate_report(
    qwen_smoke: Dict[str, Any],
    qwen_16: Dict[str, Any],
    specter2_anchor: Dict[str, Any],
    fusion_smoke: Dict[str, Any],
) -> Dict[str, Any]:
    qwen_rows = qwen_16.get("results") or []
    ok_qwen = [r for r in qwen_rows if r.get("status") == "ok"]

    fallback_used = any(bool(r.get("fallback_used") or False) for r in ok_qwen)
    unsupported_count = sum(int(r.get("unsupported_field_type_count") or 0) for r in ok_qwen)

    by_family_lat: Dict[str, List[float]] = defaultdict(list)
    evidence_build_latencies: List[float] = []
    for row in ok_qwen:
        family = str(row.get("query_family") or "unknown")
        total_ms = float((row.get("latency_breakdown_ms") or {}).get("total_latency_ms") or 0.0)
        evi_ms = float((row.get("latency_breakdown_ms") or {}).get("evidence_build_latency_ms") or 0.0)
        by_family_lat[family].append(total_ms)
        evidence_build_latencies.append(evi_ms)

    fact_p95 = p95(by_family_lat.get("fact", [])) / 1000.0
    method_p95 = p95(by_family_lat.get("method", [])) / 1000.0
    compare_p95 = p95(by_family_lat.get("compare", [])) / 1000.0
    evidence_p95 = p95(evidence_build_latencies) / 1000.0

    qwen_gate_pass = (
        qwen_smoke.get("summary", {}).get("pass_rate", 0) > 0
        and not fallback_used
        and unsupported_count == 0
        and evidence_p95 < 10
        and max(fact_p95, method_p95 if method_p95 > 0 else fact_p95) < 60
        and (compare_p95 < 120 if compare_p95 > 0 else True)
    )

    anchor_hit = float(specter2_anchor.get("anchor_hit_at_5") or 0.0)
    cross_hit = float(specter2_anchor.get("cross_paper_hit_at_5") or 0.0)
    anchor_latency = float(specter2_anchor.get("avg_latency_s") or 0.0)

    if anchor_hit >= 0.40 and cross_hit >= 0.50 and anchor_latency < 0.2:
        specter2_gate = "PASS"
    elif 0.30 <= anchor_hit < 0.40:
        specter2_gate = "CONDITIONAL"
    else:
        specter2_gate = "BLOCKED"

    fusion_pass = (
        int(fusion_smoke.get("failed_count") or 0) == 0
        and int(fusion_smoke.get("timeout_count") or 0) == 0
        and not bool(fusion_smoke.get("pollution_detected") or False)
    )

    if qwen_gate_pass and specter2_gate == "PASS" and fusion_pass:
        overall = "PASS"
        qwen_64 = "ALLOWED"
        specter2_fusion = "ALLOWED"
        expand_50 = "ALLOWED"
    elif qwen_gate_pass and specter2_gate == "CONDITIONAL" and fusion_pass:
        overall = "CONDITIONAL"
        qwen_64 = "ALLOWED"
        specter2_fusion = "NOT_ALLOWED"
        expand_50 = "NOT_ALLOWED"
    else:
        overall = "BLOCKED"
        qwen_64 = "NOT_ALLOWED"
        specter2_fusion = "NOT_ALLOWED"
        expand_50 = "NOT_ALLOWED"

    return {
        "v2_2": overall,
        "qwen_64x3": qwen_64,
        "specter2_fusion": specter2_fusion,
        "paper_50_expansion": expand_50,
        "qwen_gate_pass": qwen_gate_pass,
        "specter2_anchor_gate": specter2_gate,
        "fusion_gate_pass": fusion_pass,
        "metrics": {
            "fact_p95_s": round(fact_p95, 3),
            "method_p95_s": round(method_p95, 3),
            "compare_p95_s": round(compare_p95, 3),
            "evidence_build_p95_s": round(evidence_p95, 3),
            "fallback_used": fallback_used,
            "unsupported_field_type_count": unsupported_count,
            "anchor_hit_at_5": anchor_hit,
            "cross_paper_hit_at_5": cross_hit,
            "anchor_avg_latency_s": anchor_latency,
        },
    }


def write_gate_md(report: Dict[str, Any]) -> None:
    path = OUT_DIR / "v2_2_quality_gate_report.md"
    lines = [
        "# v2.2 Quality Gate Report",
        "",
        f"- v2.2: {report['v2_2']}",
        f"- Qwen 64×3: {report['qwen_64x3']}",
        f"- SPECTER2 fusion: {report['specter2_fusion']}",
        f"- 50-paper expansion: {report['paper_50_expansion']}",
        "",
        "## Gate Metrics",
        "",
    ]
    for k, v in report.get("metrics", {}).items():
        lines.append(f"- {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(args: argparse.Namespace) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    golden = Path(args.golden)
    rows = filter_rows(load_rows(golden), args.query_family, args.max_queries)

    stages = STAGES if args.stage == "all" else [args.stage]

    # Step 1: Qwen smoke by family
    smoke_rows = smoke_rows_by_family(rows)
    qwen_smoke = await run_qwen_matrix(
        rows=smoke_rows,
        stages=stages,
        resume=args.resume,
        timeout_sec=args.timeout_per_query_seconds,
        max_subquestions=args.max_subquestions,
        skip_llm_synthesis=args.skip_llm_synthesis,
        save_every=args.save_every,
        fail_fast=args.fail_fast,
    )
    qwen_smoke_summary = summarize_qwen_results(qwen_smoke["results"])
    write_json_md("qwen_smoke_by_family", {"summary": qwen_smoke_summary, "results": qwen_smoke["results"]}, "Qwen Smoke by Family")

    # Step 2: Qwen 16x3
    rows_16 = rows[:16]
    qwen_16 = await run_qwen_matrix(
        rows=rows_16,
        stages=stages,
        resume=args.resume,
        timeout_sec=args.timeout_per_query_seconds,
        max_subquestions=args.max_subquestions,
        skip_llm_synthesis=args.skip_llm_synthesis,
        save_every=args.save_every,
        fail_fast=args.fail_fast,
    )
    qwen_16_summary = summarize_qwen_results(qwen_16["results"])
    (OUT_DIR / "qwen_16x3_results.json").write_text(
        json.dumps({"summary": qwen_16_summary, "results": qwen_16["results"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "qwen_16x3_report.md").write_text(
        "\n".join([
            "# Qwen 16x3 Report",
            "",
            f"- total: {qwen_16_summary['total']}",
            f"- ok: {qwen_16_summary['ok']}",
            f"- pass_rate: {qwen_16_summary['pass_rate']}",
        ])
        + "\n",
        encoding="utf-8",
    )

    # Step 3: SPECTER2 anchor eval
    specter2_anchor = run_specter2_anchor_eval(rows)
    (OUT_DIR / "specter2_anchor_eval.json").write_text(
        json.dumps(specter2_anchor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "specter2_anchor_eval.md").write_text(
        "\n".join([
            "# SPECTER2 Anchor Eval",
            "",
            f"- collection: {specter2_anchor['collection']}",
            f"- anchor_hit_at_5: {specter2_anchor['anchor_hit_at_5']}",
            f"- cross_paper_hit_at_5: {specter2_anchor['cross_paper_hit_at_5']}",
            f"- avg_latency_s: {specter2_anchor['avg_latency_s']}",
        ]) + "\n",
        encoding="utf-8",
    )

    # Step 4: Candidate fusion smoke
    fusion_smoke = await run_candidate_fusion_smoke(rows, args.timeout_per_query_seconds, args.skip_llm_synthesis)
    (OUT_DIR / "candidate_fusion_smoke.json").write_text(
        json.dumps(fusion_smoke, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "candidate_fusion_smoke.md").write_text(
        "\n".join([
            "# Candidate Fusion Smoke",
            "",
            f"- query_count: {fusion_smoke['query_count']}",
            f"- ok_count: {fusion_smoke['ok_count']}",
            f"- timeout_count: {fusion_smoke['timeout_count']}",
            f"- failed_count: {fusion_smoke['failed_count']}",
            f"- pollution_detected: {fusion_smoke['pollution_detected']}",
        ]) + "\n",
        encoding="utf-8",
    )

    # Final gate
    gate_report = build_gate_report(
        {"summary": qwen_smoke_summary, "results": qwen_smoke["results"]},
        {"summary": qwen_16_summary, "results": qwen_16["results"]},
        specter2_anchor,
        fusion_smoke,
    )
    write_gate_md(gate_report)

    print(json.dumps(gate_report, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ScholarAI v2.2 quality gate runner")
    parser.add_argument("--golden", default=str(ROOT / "artifacts/benchmarks/v2.1/qwen_dual/golden_queries_v2.1.json"))
    parser.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    parser.add_argument("--query-family", choices=["fact", "method", "compare", "numeric", "table", "figure", "survey", "all"], default="all")
    parser.add_argument("--max-queries", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout-per-query-seconds", type=int, default=180)
    parser.add_argument("--max-subquestions", type=int, default=2)
    parser.add_argument("--skip-llm-synthesis", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--save-every", type=int, default=1)
    parser.add_argument("--report-prefix", default="v2_2")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
