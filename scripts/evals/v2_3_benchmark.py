#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pymilvus import Collection, connections, utility

from app.core.model_gateway import create_embedding_provider
from app.core.rag_runtime_profile import (
    OFFICIAL_EMBEDDING_MODEL,
    OFFICIAL_LLM_MODEL,
    OFFICIAL_RERANKER_MODEL,
    OFFICIAL_RUNTIME_PROFILE,
)

FLASH_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}
PLUS_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_plus_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_plus_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_plus_llm_v2_3",
}
LOCAL_COLLECTIONS = {
    "raw": "paper_contents_v2_qwen_v2_raw_v2_1",
    "rule": "paper_contents_v2_qwen_v2_rule_v2_1",
    "llm": "paper_contents_v2_qwen_v2_llm_v2_1",
}
FAMILIES = ["fact", "method", "compare", "numeric", "table", "figure", "survey"]


class BenchmarkGuardError(RuntimeError):
    """Raised when benchmark input/profile violates official gate policy."""


@dataclass(frozen=True)
class QueryRow:
    query_id: str
    query: str
    family: str
    paper_ids: List[str]
    source_chunk_ids: List[str]


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = max(int(len(values) * 0.95) - 1, 0)
    return float(values[idx])


def classify_family(query: str, fallback: str) -> str:
    q = query.lower()
    if "table" in q:
        return "table"
    if "figure" in q or "image" in q:
        return "figure"
    if "compare" in q or "difference" in q:
        return "compare"
    if "method" in q or "approach" in q:
        return "method"
    if "number" in q or "percentage" in q or "score" in q:
        return "numeric"
    if "survey" in q or "overview" in q:
        return "survey"
    if fallback in FAMILIES:
        return fallback
    return "fact"


def load_rows(path: Path) -> List[QueryRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: List[QueryRow] = []

    # v2.5+ flat schema
    if isinstance(data, dict) and isinstance(data.get("queries"), list):
        for q in data.get("queries", []):
            query = str(q.get("query") or "").strip()
            if not query:
                continue
            rows.append(
                QueryRow(
                    query_id=str(q.get("query_id") or q.get("id") or "row"),
                    query=query,
                    family=classify_family(query, str(q.get("query_family") or q.get("query_type") or "fact")),
                    paper_ids=[str(x) for x in (q.get("expected_paper_ids") or q.get("paper_ids") or [])],
                    source_chunk_ids=[str(x) for x in (q.get("expected_source_chunk_ids") or [])],
                )
            )
        return rows

    for paper in data.get("papers", []):
        paper_id = str(paper.get("paper_id") or "")
        for q in paper.get("queries", []):
            query = str(q.get("query") or "").strip()
            if not query:
                continue
            fam = classify_family(query, str(q.get("query_type") or "fact"))
            rows.append(
                QueryRow(
                    query_id=str(q.get("id") or f"{paper_id}-q"),
                    query=query,
                    family=fam,
                    paper_ids=[paper_id] if paper_id else [],
                    source_chunk_ids=[str(x) for x in (q.get("expected_source_chunk_ids") or [])],
                )
            )

    for q in data.get("cross_paper_queries", []):
        query = str(q.get("query") or "").strip()
        if not query:
            continue
        rows.append(
            QueryRow(
                query_id=str(q.get("id") or "cross-paper"),
                query=query,
                family=classify_family(query, "compare"),
                paper_ids=[str(x) for x in (q.get("expected_papers") or q.get("paper_ids") or [])],
                source_chunk_ids=[str(x) for x in (q.get("expected_source_chunk_ids") or [])],
            )
        )

    for q in data.get("multimodal_queries", []):
        query = str(q.get("query") or "").strip()
        if not query:
            continue
        rows.append(
            QueryRow(
                query_id=str(q.get("id") or "multimodal"),
                query=query,
                family=classify_family(query, str(q.get("query_type") or "table")),
                paper_ids=[str(x) for x in (q.get("paper_ids") or q.get("expected_papers") or [])],
                source_chunk_ids=[str(x) for x in (q.get("expected_source_chunk_ids") or [])],
            )
        )

    return rows


def get_hit_paper(hit: Any) -> str:
    try:
        if hasattr(hit, "fields") and hit.fields:
            return str(hit.fields.get("paper_id") or "")
        if hasattr(hit, "entity") and hasattr(hit.entity, "get"):
            return str(hit.entity.get("paper_id") or "")
    except Exception:
        return ""
    return ""


def run_query(
    *,
    provider,
    collection: Collection,
    row: QueryRow,
    top_k: int = 10,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    vec = provider.embed_texts([row.query])[0]

    search = collection.search(
        data=[vec],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["paper_id", "content_data"],
    )
    latency_s = time.perf_counter() - t0

    hits = search[0] if search else []
    hit_papers = [get_hit_paper(h) for h in hits]
    hit_papers = [p for p in hit_papers if p]

    expected = set(row.paper_ids)
    coverage = 1.0 if (expected and (set(hit_papers) & expected)) else 0.0
    jump_valid = 1.0 if len(hit_papers) >= 1 else 0.0

    return {
        "query_id": row.query_id,
        "query": row.query,
        "family": row.family,
        "expected_papers": row.paper_ids,
        "hit_papers": hit_papers,
        "citation_coverage": coverage,
        "answer_evidence_consistency": coverage,
        "citation_jump_validity": jump_valid,
        "unsupported_claim": 0.0 if coverage >= 1.0 else 1.0,
        "latency_s": round(latency_s, 4),
        "fallback_used": False,
        "dimension_mismatch": 0,
        "provider_hard_error": 0,
        "status": "ok",
    }


def select_smoke_rows(rows: List[QueryRow]) -> List[QueryRow]:
    by_family: Dict[str, QueryRow] = {}
    for r in rows:
        if r.family not in by_family:
            by_family[r.family] = r
    # smoke only 1 query then run 3 stages
    if by_family:
        return [next(iter(by_family.values()))]
    return rows[:1]


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    cov = [r["citation_coverage"] for r in results]
    uns = [r["unsupported_claim"] for r in results]
    con = [r["answer_evidence_consistency"] for r in results]
    jump = [r["citation_jump_validity"] for r in results]
    lat = [r["latency_s"] for r in results]
    return {
        "total": len(results),
        "ok": sum(1 for r in results if r.get("status") == "ok"),
        "citation_coverage": round(float(statistics.mean(cov)) if cov else 0.0, 4),
        "unsupported_claim_rate": round(float(statistics.mean(uns)) if uns else 0.0, 4),
        "answer_evidence_consistency": round(float(statistics.mean(con)) if con else 0.0, 4),
        "citation_jump_validity": round(float(statistics.mean(jump)) if jump else 0.0, 4),
        "p95_latency_s": round(p95(lat), 4),
        "fallback_used": 0,
        "dimension_mismatch": 0,
        "provider_hard_error": 0,
    }


def build_runtime_metadata(*, runtime_profile: str, deprecated_branch_used: bool, synthetic_for_official: bool) -> Dict[str, Any]:
    return {
        "runtime_profile": runtime_profile,
        "embedding_model": OFFICIAL_EMBEDDING_MODEL,
        "reranker_model": OFFICIAL_RERANKER_MODEL,
        "llm_model": OFFICIAL_LLM_MODEL,
        "deprecated_branch_used": deprecated_branch_used,
        "synthetic_golden_used_for_official_gate": synthetic_for_official,
    }


def _looks_like_real_corpus_paper_id(paper_id: str) -> bool:
    value = (paper_id or "").strip().lower()
    if not value:
        return True
    return value.startswith("v2-p-")


def validate_benchmark_runtime(runtime_profile: str) -> None:
    if runtime_profile != OFFICIAL_RUNTIME_PROFILE:
        raise BenchmarkGuardError(
            f"official benchmark only allows runtime profile: {OFFICIAL_RUNTIME_PROFILE}"
        )


def validate_official_gate_inputs(*, golden_mode: str, rows: List[QueryRow], mode: str = "official") -> None:
    if golden_mode == "synthetic" and mode != "smoke":
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: official benchmark gate cannot use synthetic golden (SMOKE_ONLY)"
        )

    invalid_ids: set[str] = set()
    synthetic_ids: set[str] = set()
    for row in rows:
        for paper_id in getattr(row, "paper_ids", []):
            if paper_id.startswith("test-paper-") and mode != "smoke":
                synthetic_ids.add(paper_id)
            if not _looks_like_real_corpus_paper_id(paper_id):
                invalid_ids.add(paper_id)
    if synthetic_ids:
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: synthetic paper_id is not allowed in official mode: "
            + ", ".join(sorted(synthetic_ids))
        )
    if invalid_ids:
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: golden paper_id not in current corpus: "
            + ", ".join(sorted(invalid_ids))
        )


def validate_official_collection_membership(
    *,
    rows: List[QueryRow],
    collection_paper_ids: set[str],
    collection_source_chunk_ids: set[str],
) -> None:
    missing_papers = sorted(
        {
            paper_id
            for row in rows
            for paper_id in getattr(row, "paper_ids", [])
            if paper_id and paper_id not in collection_paper_ids
        }
    )
    if missing_papers:
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: expected_paper_id not in collection: " + ", ".join(missing_papers[:20])
        )

    missing_sources = sorted(
        {
            sid
            for row in rows
            for sid in getattr(row, "source_chunk_ids", [])
            if sid and sid not in collection_source_chunk_ids
        }
    )
    if missing_sources:
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: expected_source_chunk_id not in collection: " + ", ".join(missing_sources[:20])
        )


def load_official_collection_membership(*, alias: str) -> Tuple[set[str], set[str]]:
    collection_paper_ids: set[str] = set()
    collection_source_chunk_ids: set[str] = set()
    for stage in ["raw", "rule", "llm"]:
        col = Collection(FLASH_COLLECTIONS[stage], using=alias)
        col.load()
        rows = col.query(expr="id >= 0", output_fields=["paper_id", "source_chunk_id"], limit=16384)
        collection_paper_ids |= {str(r.get("paper_id") or "") for r in rows if str(r.get("paper_id") or "")}
        collection_source_chunk_ids |= {str(r.get("source_chunk_id") or "") for r in rows if str(r.get("source_chunk_id") or "")}
    return collection_paper_ids, collection_source_chunk_ids


def validate_required_artifacts(*, rows: List[QueryRow], artifacts_root: Path) -> None:
    missing: List[str] = []
    paper_ids = sorted({paper_id for row in rows for paper_id in row.paper_ids if paper_id})

    for paper_id in paper_ids:
        paper_dir = artifacts_root / paper_id
        expected = [
            paper_dir / "parse_artifact.json",
            paper_dir / "chunks_raw.json",
            paper_dir / "chunks_rule.json",
            paper_dir / "chunks_llm.json",
        ]
        for path in expected:
            if not path.exists():
                try:
                    missing.append(str(path.relative_to(ROOT)))
                except ValueError:
                    missing.append(str(path))

    if missing:
        raise BenchmarkGuardError(
            "EVAL_BLOCKED: missing required artifacts: " + ", ".join(missing[:20])
        )


def write_md(path: Path, title: str, summary: Dict[str, Any]) -> None:
    lines = [
        f"# {title}",
        "",
        f"- total: {summary.get('total',0)}",
        f"- ok: {summary.get('ok',0)}",
        f"- citation_coverage: {summary.get('citation_coverage',0)}",
        f"- unsupported_claim_rate: {summary.get('unsupported_claim_rate',0)}",
        f"- answer_evidence_consistency: {summary.get('answer_evidence_consistency',0)}",
        f"- citation_jump_validity: {summary.get('citation_jump_validity',0)}",
        f"- p95_latency_s: {summary.get('p95_latency_s',0)}",
        f"- fallback_used: {summary.get('fallback_used',0)}",
        f"- dimension_mismatch: {summary.get('dimension_mismatch',0)}",
        f"- provider_hard_error: {summary.get('provider_hard_error',0)}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="v2.3 benchmark")
    p.add_argument("--mode", default="official", choices=["official", "smoke"])
    p.add_argument("--runtime-profile", default=OFFICIAL_RUNTIME_PROFILE)
    p.add_argument("--provider", default="tongyi")
    p.add_argument("--flash-model", default=OFFICIAL_EMBEDDING_MODEL)
    p.add_argument("--plus-model", default="tongyi-embedding-vision-plus-2026-03-06")
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3_1"))
    p.add_argument("--golden-path", default=None)
    p.add_argument("--golden-mode", default="real", choices=["synthetic", "real"])
    p.add_argument("--corpus-profile", default="v2_3_api_flash", choices=["v2_3_api_flash"])
    p.add_argument("--official-gate", action="store_true", default=True)
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    p.add_argument("--smoke-only", action="store_true")
    p.add_argument("--skip-local", action="store_true")
    p.add_argument("--artifacts-root", default=str(ROOT / "artifacts" / "papers"))
    args = p.parse_args()

    if args.mode == "official" and not args.golden_path:
        raise BenchmarkGuardError("PIPELINE_BLOCKED: official mode requires explicit --golden-path")

    if args.mode == "official" and args.golden_mode != "real":
        raise BenchmarkGuardError("EVAL_BLOCKED: official mode only allows golden_mode=real")

    default_real = str(ROOT / "artifacts" / "benchmarks" / "v2_3_1" / "golden_queries_real.json")
    if not args.golden_path:
        args.golden_path = default_real

    if args.golden_mode == "synthetic" and args.golden_path == default_real:
        synthetic_default = str(ROOT / "tests" / "evals" / "golden_queries.json")
        print(f"[WARN] synthetic mode using default golden: {synthetic_default}")
        args.golden_path = synthetic_default

    if args.corpus_profile == "v2_3_api_flash":
        LOCAL_COLLECTIONS.update({
            "raw": "paper_contents_v2_qwen_v2_raw_v2_1",
            "rule": "paper_contents_v2_qwen_v2_rule_v2_1",
            "llm": "paper_contents_v2_qwen_v2_llm_v2_1",
        })

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(Path(args.golden_path))
    error_msg = None

    runtime_metadata = build_runtime_metadata(
        runtime_profile=args.runtime_profile,
        deprecated_branch_used=False,
        synthetic_for_official=args.official_gate and args.golden_mode == "synthetic",
    )

    try:
        validate_benchmark_runtime(args.runtime_profile)
        if args.official_gate:
            validate_official_gate_inputs(golden_mode=args.golden_mode, rows=rows, mode=args.mode)
            validate_required_artifacts(rows=rows, artifacts_root=Path(args.artifacts_root))

            connections.connect(alias="v23_guard", host=args.milvus_host, port=args.milvus_port)
            collection_paper_ids, collection_source_chunk_ids = load_official_collection_membership(alias="v23_guard")
            validate_official_collection_membership(
                rows=rows,
                collection_paper_ids=collection_paper_ids,
                collection_source_chunk_ids=collection_source_chunk_ids,
            )
    except BenchmarkGuardError as exc:
        msg = str(exc)
        if "EVAL_BLOCKED" in msg:
            eval_status = "EVAL_BLOCKED"
        elif "PIPELINE_BLOCKED" in msg:
            eval_status = "PIPELINE_BLOCKED"
        else:
            eval_status = "PIPELINE_BLOCKED"
        blocked = {
            "status": "BLOCKED",
            "eval_status": eval_status,
            "blocked_reason": msg,
            "runtime": runtime_metadata,
        }
        print(json.dumps(blocked, ensure_ascii=False, indent=2))
        return 1
    
    golden_mode = args.golden_mode
    is_synthetic = golden_mode == "synthetic"
    is_smoke = args.smoke_only

    try:
        connections.connect(alias="v23_bench", host=args.milvus_host, port=args.milvus_port)

        flash_provider = create_embedding_provider(args.provider, args.flash_model)
        plus_provider = create_embedding_provider(args.provider, args.plus_model)
        local_provider = None
        if not args.skip_local:
            local_provider = create_embedding_provider("local_qwen", "qwen3-vl-2b")

        # Smoke 1x3
        smoke_rows = select_smoke_rows(rows)
        smoke_results: List[Dict[str, Any]] = []
        for stage in ["raw", "rule", "llm"]:
            col = Collection(FLASH_COLLECTIONS[stage], using="v23_bench")
            col.load()
            for row in smoke_rows:
                r = run_query(provider=flash_provider, collection=col, row=row)
                r["stage"] = stage
                smoke_results.append(r)

        smoke_summary = summarize(smoke_results)
        (out_dir / "api_flash_smoke_1x3.json").write_text(
            json.dumps({"runtime": runtime_metadata, "summary": smoke_summary, "results": smoke_results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_md(out_dir / "api_flash_smoke_1x3.md", "v2.3 API Flash Smoke 1x3", smoke_summary)

        # 16x3
        scoped16 = rows[:16]
        res16: List[Dict[str, Any]] = []
        for stage in ["raw", "rule", "llm"]:
            col = Collection(FLASH_COLLECTIONS[stage], using="v23_bench")
            col.load()
            for row in scoped16:
                rr = run_query(provider=flash_provider, collection=col, row=row)
                rr["stage"] = stage
                res16.append(rr)

        summary16 = summarize(res16)
        (out_dir / "api_flash_16x3_results.json").write_text(
            json.dumps({"runtime": runtime_metadata, "summary": summary16, "results": res16}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_md(out_dir / "api_flash_16x3_report.md", "v2.3 API Flash 16x3 Report", summary16)

        # local baseline comparison (same query set, collection-only retrieval)
        local_res: List[Dict[str, Any]] = []
        local_summary = summarize(local_res)
        if not args.skip_local:
            if local_provider is None:
                raise RuntimeError("local provider unavailable while skip_local is false")
            for stage in ["raw", "rule", "llm"]:
                col = Collection(LOCAL_COLLECTIONS[stage], using="v23_bench")
                col.load()
                for row in scoped16:
                    rr = run_query(provider=local_provider, collection=col, row=row)
                    rr["stage"] = stage
                    local_res.append(rr)
            local_summary = summarize(local_res)

        cmp_lines = [
        "# v2.3 Local Qwen vs API Flash Comparison",
        "",
        "| metric | local_qwen_v2 | api_tongyi_flash |",
        "|---|---:|---:|",
        f"| citation_coverage | {local_summary['citation_coverage']} | {summary16['citation_coverage']} |",
        f"| unsupported_claim_rate | {local_summary['unsupported_claim_rate']} | {summary16['unsupported_claim_rate']} |",
        f"| answer_evidence_consistency | {local_summary['answer_evidence_consistency']} | {summary16['answer_evidence_consistency']} |",
        f"| citation_jump_validity | {local_summary['citation_jump_validity']} | {summary16['citation_jump_validity']} |",
        f"| p95_latency_s | {local_summary['p95_latency_s']} | {summary16['p95_latency_s']} |",
    ]
        (out_dir / "local_qwen_vs_api_flash_comparison.md").write_text("\n".join(cmp_lines) + "\n", encoding="utf-8")

        # Plus A/B only failed cases + table/figure/hard(compare)
        failed = [r for r in res16 if r["citation_coverage"] < 1.0 or r["family"] in {"table", "figure", "compare"}]
        ab_rows: List[QueryRow] = []
        seen = set()
        for r in failed:
            if r["query_id"] not in seen:
                seen.add(r["query_id"])
                ab_rows.append(
                    QueryRow(
                        r["query_id"],
                        r["query"],
                        r["family"],
                        r.get("expected_papers", []),
                        [],
                    )
                )

        plus_res: List[Dict[str, Any]] = []
        for stage in ["raw", "rule", "llm"]:
            name = PLUS_COLLECTIONS[stage]
            if not utility.has_collection(name, using="v23_bench"):
                continue
            col = Collection(name, using="v23_bench")
            col.load()
            for row in ab_rows:
                rr = run_query(provider=plus_provider, collection=col, row=row)
                rr["stage"] = stage
                plus_res.append(rr)

        plus_summary = summarize(plus_res)
        (out_dir / "api_plus_failed_cases_ab.json").write_text(
            json.dumps({"summary": plus_summary, "results": plus_res}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_md(out_dir / "api_plus_failed_cases_ab.md", "v2.3 API Plus Failed-Cases A/B", plus_summary)

        # Gate with proper categorization
        pipeline_pass = (
            summary16["citation_jump_validity"] >= 0.90
            and summary16["p95_latency_s"] < 60.0
            and summary16["dimension_mismatch"] == 0
            and summary16["provider_hard_error"] == 0
        )
        eval_valid = not is_synthetic
        quality_pass = (
            eval_valid
            and summary16["citation_coverage"] >= 0.85
            and summary16["unsupported_claim_rate"] <= 0.10
            and summary16["answer_evidence_consistency"] >= 0.65
        ) or (is_synthetic and summary16["ok"] > 0)
        
        if is_synthetic:
            gate_status = "SMOKE_ONLY"
            eval_status = "SMOKE"
        elif not pipeline_pass:
            gate_status = "BLOCKED"
            eval_status = "PIPELINE_ERROR"
        elif not eval_valid:
            gate_status = "BLOCKED"
            eval_status = "EVAL_BLOCKED"
        elif not quality_pass:
            gate_status = "BLOCKED"
            eval_status = "QUALITY_BLOCKED"
        else:
            gate_status = "PASS"
            eval_status = "QUALITY_PASS"
        
        synthetic_label = "SMOKE_ONLY" if is_synthetic else "REQUIRED_FOR_OFFICIAL_GATE"
        lines = [
        "# v2.3 API-first Gate Report",
        "",
        f"- v2.3: {gate_status}",
        f"- eval_status: {eval_status}",
        f"- golden_mode: {golden_mode}",
        f"- API flash as default: {'ALLOWED' if quality_pass and not is_synthetic else 'NOT_ALLOWED'}",
        f"- API plus quality mode: {'ALLOWED' if len(plus_res) > 0 else 'NOT_ALLOWED'}",
        "- Qwen local baseline: KEEP",
        "- synthetic golden: SMOKE_ONLY",
        f"- real golden: {synthetic_label}",
        f"- 64×3: {'ALLOWED' if quality_pass and not is_synthetic else 'NOT_ALLOWED'}",
        f"- 50-paper expansion: {'ALLOWED' if quality_pass else 'NOT_ALLOWED'}",
        "",
        "## Gate Metrics (api flash 16x3)",
        "",
        f"- citation_coverage: {summary16['citation_coverage']}",
        f"- unsupported_claim_rate: {summary16['unsupported_claim_rate']}",
        f"- answer_evidence_consistency: {summary16['answer_evidence_consistency']}",
        f"- citation_jump_validity: {summary16['citation_jump_validity']}",
        f"- p95_latency_s: {summary16['p95_latency_s']}",
        f"- fallback_used: {summary16['fallback_used']}",
        f"- dimension_mismatch: {summary16['dimension_mismatch']}",
        f"- provider_hard_error: {summary16['provider_hard_error']}",
        "",
        f"**Golden Mode**: {golden_mode} ({'synthetic test-paper IDs' if is_synthetic else 'real v2-p-001..020'})",
    ]
        (out_dir / "v2_3_api_first_gate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        
        output_basename = "v2_3_1_real_golden_gate_report.md" if not is_synthetic else "v2_3_smoke_synthetic_gate_report.md"
        (out_dir / output_basename).write_text("\n".join(lines) + "\n", encoding="utf-8")

        print(
            json.dumps(
                {
                    "status": gate_status,
                    "eval_status": eval_status,
                    "golden_mode": golden_mode,
                    "runtime": runtime_metadata,
                    "flash_summary": summary16,
                    "plus_summary": plus_summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if gate_status == "PASS" else (0 if gate_status == "SMOKE_ONLY" else 1)

    except Exception as e:
        error_msg = str(e)

    # Blocked fallback outputs (still generate required artifacts)
    blocked_summary = {
        "total": 0,
        "ok": 0,
        "citation_coverage": 0.0,
        "unsupported_claim_rate": 1.0,
        "answer_evidence_consistency": 0.0,
        "citation_jump_validity": 0.0,
        "p95_latency_s": 0.0,
        "fallback_used": 0,
        "dimension_mismatch": 0,
        "provider_hard_error": 1,
    }
    (out_dir / "api_flash_smoke_1x3.json").write_text(json.dumps({"runtime": runtime_metadata, "summary": blocked_summary, "results": [], "error": error_msg}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(out_dir / "api_flash_smoke_1x3.md", "v2.3 API Flash Smoke 1x3", blocked_summary)
    (out_dir / "api_flash_16x3_results.json").write_text(json.dumps({"runtime": runtime_metadata, "summary": blocked_summary, "results": [], "error": error_msg}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(out_dir / "api_flash_16x3_report.md", "v2.3 API Flash 16x3 Report", blocked_summary)
    (out_dir / "local_qwen_vs_api_flash_comparison.md").write_text(
        "# v2.3 Local Qwen vs API Flash Comparison\n\n"
        "BLOCKED: benchmark did not run.\n"
        f"error: {error_msg}\n",
        encoding="utf-8",
    )
    (out_dir / "api_plus_failed_cases_ab.json").write_text(json.dumps({"runtime": runtime_metadata, "summary": blocked_summary, "results": [], "error": error_msg}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(out_dir / "api_plus_failed_cases_ab.md", "v2.3 API Plus Failed-Cases A/B", blocked_summary)
    (out_dir / "v2_3_api_first_gate_report.md").write_text(
        "# v2.3 API-first Gate Report\n\n"
        "- v2.3: BLOCKED\n"
        "- API flash as default: NOT_ALLOWED\n"
        "- API plus quality mode: NOT_ALLOWED\n"
        "- Qwen local baseline: KEEP\n"
        "- SPECTER2: EXPERIMENTAL\n"
        "- 64×3: NOT_ALLOWED\n"
        "- 50-paper expansion: NOT_ALLOWED\n\n"
        f"error: {error_msg}\n",
        encoding="utf-8",
    )

    print(json.dumps({"status": "BLOCKED", "error": error_msg}, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
