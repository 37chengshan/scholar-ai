#!/usr/bin/env python3
"""v3.0 Phase 1 Paper/Section Recall Evaluation.

Implements RAPTOR-style hierarchical retrieval evaluation:
  - Builds paper-level and section-level summary indexes from artifact chunks
  - Runs hierarchical retrieval (paper-level → section-level → dense Milvus)
  - Computes paper_hit@10, section_hit@10, candidate_pool_oracle_recall@100
  - Compares against v2_6_2 baseline frozen in artifacts/benchmarks/v3_0/

PASS thresholds (Phase 1):
  paper_hit@10        >= 0.70
  section_hit@10      >= 0.50
  oracle_recall@100   >= 0.60
  exact_recall@10     >= 0.30
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in [str(API_ROOT), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.evals.v2_4_common import stage_collection_name

OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_0"
DOC_DIR = ROOT / "docs" / "reports" / "official_rag_evaluation"
BASELINE_PATH = OUTPUT_DIR / "v2_failure_baseline.json"
GOLDEN_PATH = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
ARTIFACT_PAPERS_ROOT = ROOT / "artifacts" / "papers"

EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"
COLLECTION_SUFFIX = "v2_4"

PASS_THRESHOLDS = {
    "paper_hit_at_10": 0.70,
    "section_hit_at_10": 0.50,
    "oracle_recall_at_100": 0.60,
    "exact_recall_at_10": 0.30,
}


@dataclass
class GoldenRow:
    query_id: str
    query: str
    query_family: str
    expected_paper_ids: list[str]
    expected_source_chunk_ids: list[str]
    expected_sections: list[str]


@dataclass
class EvalResult:
    query_id: str
    query_family: str
    paper_hit: int          # 1 if any expected paper in top-10
    section_hit: int        # 1 if any expected section in top-10
    exact_hit: int          # 1 if any expected source_chunk_id in top-10
    oracle_hit_100: int     # 1 if expected paper in candidate pool of 100
    paper_ids_top10: list[str]
    sections_top10: list[str]
    chunk_ids_top10: list[str]
    dense_retrieved: int
    paper_index_size: int
    section_index_size: int
    latency_ms: float
    failure_bucket: str     # paper_miss / section_miss / candidate_pool_miss / exact_miss / pass


def load_golden(path: Path, max_queries: int | None = None) -> list[GoldenRow]:
    data = json.loads(path.read_text())
    queries = data["queries"] if isinstance(data, dict) else data
    rows: list[GoldenRow] = []
    for q in queries:
        rows.append(
            GoldenRow(
                query_id=q["query_id"],
                query=q["query"],
                query_family=q.get("query_family", "fact"),
                expected_paper_ids=[str(p) for p in (q.get("expected_paper_ids") or [])],
                expected_source_chunk_ids=[str(c) for c in (q.get("expected_source_chunk_ids") or [])],
                expected_sections=[str(s) for s in (q.get("expected_sections") or [])],
            )
        )
    if max_queries:
        rows = rows[:max_queries]
    return rows


def classify_failure(result: EvalResult) -> str:
    if result.paper_hit == 0:
        return "paper_miss"
    if result.section_hit == 0:
        return "section_miss"
    if result.oracle_hit_100 == 0:
        return "candidate_pool_miss"
    if result.exact_hit == 0:
        return "exact_miss"
    return "pass"


def run_eval(
    args: argparse.Namespace,
) -> tuple[list[EvalResult], dict[str, Any]]:
    from pymilvus import Collection, connections

    from app.core.model_gateway import create_embedding_provider
    from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
    from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
    from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever

    print(f"[v3.0 Phase 1] Building summary indexes from: {ARTIFACT_PAPERS_ROOT}")
    t0 = time.perf_counter()
    paper_index, section_index = build_indexes_from_artifacts(
        artifact_root=ARTIFACT_PAPERS_ROOT,
        stage=args.stage,
    )
    index_build_sec = time.perf_counter() - t0
    print(f"  Papers indexed: {len(paper_index)}  Sections indexed: {len(section_index)}  ({index_build_sec:.1f}s)")

    print(f"[v3.0 Phase 1] Connecting to Milvus {args.milvus_host}:{args.milvus_port}")
    connections.connect(alias="v3_phase1", host=args.milvus_host, port=args.milvus_port)
    embedding_provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)

    collection_name = stage_collection_name(args.stage, COLLECTION_SUFFIX)
    dense_retriever = DenseEvidenceRetriever(
        embedding_provider=embedding_provider,
        collection_name=collection_name,
        milvus_alias="v3_phase1",
        output_fields=["source_chunk_id", "paper_id", "normalized_section_path", "content_type", "anchor_text"],
    )

    retriever = HierarchicalRetriever(
        paper_index=paper_index,
        section_index=section_index,
        dense_retriever=dense_retriever,
    )

    golden_rows = load_golden(GOLDEN_PATH, max_queries=args.max_queries)
    print(f"[v3.0 Phase 1] Evaluating {len(golden_rows)} queries on stage={args.stage} ...")

    results: list[EvalResult] = []
    for idx, row in enumerate(golden_rows, 1):
        t_start = time.perf_counter()
        pack = retriever.retrieve_evidence(
            query=row.query,
            query_family=row.query_family,
            stage=args.stage,
            top_k=10,
        )
        latency_ms = (time.perf_counter() - t_start) * 1000

        paper_ids_top10 = [c.paper_id for c in pack.candidates[:10]]
        sections_top10 = [c.section_id for c in pack.candidates[:10]]
        chunk_ids_top10 = [c.source_chunk_id for c in pack.candidates[:10]]

        # Oracle: use larger candidate pool
        t_oracle = time.perf_counter()
        from app.rag_v3.retrieval.dense_evidence_retriever import extract_paper_ids_from_query as _epid
        _oracle_filter = _epid(row.query) or None
        oracle_pack = retriever._dense_retriever.retrieve(query=row.query, top_k=100, paper_id_filter=_oracle_filter)
        oracle_paper_ids = {c.paper_id for c in oracle_pack[:100]}

        expected_set = set(row.expected_paper_ids)
        expected_chunks = set(row.expected_source_chunk_ids)
        expected_sections_set = set(row.expected_sections)

        paper_hit = 1 if expected_set & set(paper_ids_top10) else 0
        exact_hit = 1 if expected_chunks & set(chunk_ids_top10) else 0
        oracle_hit = 1 if expected_set & oracle_paper_ids else 0

        # Section hit: check if any expected section appears as substring of retrieved sections
        section_hit = 0
        for es in expected_sections_set:
            for rs in sections_top10:
                if es and es.lower() in rs.lower():
                    section_hit = 1
                    break

        result = EvalResult(
            query_id=row.query_id,
            query_family=row.query_family,
            paper_hit=paper_hit,
            section_hit=section_hit,
            exact_hit=exact_hit,
            oracle_hit_100=oracle_hit,
            paper_ids_top10=paper_ids_top10,
            sections_top10=sections_top10[:10],
            chunk_ids_top10=chunk_ids_top10,
            dense_retrieved=int(pack.diagnostics.get("dense_retrieved", 0)),
            paper_index_size=int(pack.diagnostics.get("paper_index_size", 0)),
            section_index_size=int(pack.diagnostics.get("section_index_size", 0)),
            latency_ms=latency_ms,
            failure_bucket="",
        )
        result.failure_bucket = classify_failure(result)
        results.append(result)

        if idx % 5 == 0 or idx == len(golden_rows):
            ph = sum(r.paper_hit for r in results) / len(results)
            sh = sum(r.section_hit for r in results) / len(results)
            eh = sum(r.exact_hit for r in results) / len(results)
            print(f"  [{idx:3d}/{len(golden_rows)}] paper_hit={ph:.3f}  section_hit={sh:.3f}  exact={eh:.3f}  latency={latency_ms:.0f}ms")

    # Aggregate metrics
    n = len(results)
    by_family: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_family[r.query_family].append(r)

    def agg(items: list[EvalResult]) -> dict[str, float]:
        if not items:
            return {}
        return {
            "total": len(items),
            "paper_hit_at_10": round(sum(r.paper_hit for r in items) / len(items), 4),
            "section_hit_at_10": round(sum(r.section_hit for r in items) / len(items), 4),
            "exact_recall_at_10": round(sum(r.exact_hit for r in items) / len(items), 4),
            "oracle_recall_at_100": round(sum(r.oracle_hit_100 for r in items) / len(items), 4),
            "avg_latency_ms": round(sum(r.latency_ms for r in items) / len(items), 1),
        }

    summary = {
        "overall": agg(results),
        "by_family": {fam: agg(items) for fam, items in by_family.items()},
        "failure_buckets": {
            bucket: sum(1 for r in results if r.failure_bucket == bucket)
            for bucket in ["pass", "paper_miss", "section_miss", "candidate_pool_miss", "exact_miss"]
        },
    }

    return results, summary


def check_gates(summary: dict[str, Any]) -> tuple[str, dict[str, bool]]:
    overall = summary["overall"]
    gate_results = {
        f"paper_hit_at_10 >= {PASS_THRESHOLDS['paper_hit_at_10']}": overall.get("paper_hit_at_10", 0) >= PASS_THRESHOLDS["paper_hit_at_10"],
        f"section_hit_at_10 >= {PASS_THRESHOLDS['section_hit_at_10']}": overall.get("section_hit_at_10", 0) >= PASS_THRESHOLDS["section_hit_at_10"],
        f"oracle_recall_at_100 >= {PASS_THRESHOLDS['oracle_recall_at_100']}": overall.get("oracle_recall_at_100", 0) >= PASS_THRESHOLDS["oracle_recall_at_100"],
        f"exact_recall_at_10 >= {PASS_THRESHOLDS['exact_recall_at_10']}": overall.get("exact_recall_at_10", 0) >= PASS_THRESHOLDS["exact_recall_at_10"],
    }
    verdict = "PASS" if all(gate_results.values()) else "PARTIAL" if any(gate_results.values()) else "FAIL"
    return verdict, gate_results


def build_markdown_report(
    summary: dict[str, Any],
    verdict: str,
    gate_results: dict[str, bool],
    baseline_metrics: dict[str, float],
    args: argparse.Namespace,
) -> str:
    overall = summary["overall"]
    lines: list[str] = [
        "# v3.0 Phase 1 — Paper/Section Recall Evaluation Report",
        "",
        f"**Stage**: `{args.stage}`  |  **Verdict**: `{verdict}`",
        "",
        "## Overall Metrics vs. v2.6.2 Baseline",
        "",
        "| Metric | v2.6.2 Baseline | v3.0 Phase 1 | Delta | Gate |",
        "|--------|----------------|--------------|-------|------|",
    ]

    metric_map = [
        ("paper_hit_at_10", "paper_hit_rate", "paper_hit_at_10"),
        ("section_hit_at_10", "same_section_hit", "section_hit_at_10"),
        ("oracle_recall_at_100", "recall_at_100", "oracle_recall_at_100"),
        ("exact_recall_at_10", "recall_at_10", "exact_recall_at_10"),
    ]
    for v3_key, v2_key, gate_key in metric_map:
        v2_val = baseline_metrics.get(v2_key, 0.0)
        v3_val = overall.get(v3_key, 0.0)
        delta = v3_val - v2_val
        delta_str = f"+{delta:.4f}" if delta >= 0 else f"{delta:.4f}"
        threshold = PASS_THRESHOLDS.get(gate_key, 0)
        gate_icon = "✅" if v3_val >= threshold else "❌"
        lines.append(f"| {v3_key} | {v2_val:.4f} | {v3_val:.4f} | {delta_str} | {gate_icon} >= {threshold} |")

    lines += [
        "",
        "## Gate Results",
        "",
    ]
    for gate, passed in gate_results.items():
        icon = "✅ PASS" if passed else "❌ FAIL"
        lines.append(f"- {icon}: `{gate}`")

    lines += [
        "",
        "## Failure Bucket Distribution",
        "",
        "| Bucket | Count |",
        "|--------|-------|",
    ]
    for bucket, count in sorted(summary["failure_buckets"].items()):
        lines.append(f"| {bucket} | {count} |")

    lines += [
        "",
        "## By Query Family",
        "",
        "| Family | N | paper_hit | section_hit | exact | oracle@100 |",
        "|--------|---|-----------|-------------|-------|------------|",
    ]
    for fam, fam_metrics in sorted(summary["by_family"].items()):
        lines.append(
            f"| {fam} | {fam_metrics.get('total',0)} "
            f"| {fam_metrics.get('paper_hit_at_10',0):.3f} "
            f"| {fam_metrics.get('section_hit_at_10',0):.3f} "
            f"| {fam_metrics.get('exact_recall_at_10',0):.3f} "
            f"| {fam_metrics.get('oracle_recall_at_100',0):.3f} |"
        )

    lines += ["", "## Notes", "", "- Index built from `artifacts/papers/` chunk files (no re-parsing, no re-chunking).", "- Dense retrieval uses Milvus `paper_contents_v2_api_tongyi_flash_{stage}_v2_4`.", "- Section hit uses substring match against `normalized_section_path`.", ""]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v3.0 Phase 1 Paper/Section Recall Eval")
    p.add_argument("--stage", choices=["raw", "rule", "llm"], default="raw")
    p.add_argument("--max-queries", type=int, default=None)
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    # Load baseline metrics for comparison
    baseline_metrics: dict[str, float] = {}
    if BASELINE_PATH.exists():
        baseline_data = json.loads(BASELINE_PATH.read_text())
        raw_metrics = baseline_data.get("metrics", {})
        # Map v3_0 freeze format to v2.6.2 collection-level metrics
        baseline_metrics = {
            "recall_at_10": raw_metrics.get("recall_at_10", 0.0),
            "recall_at_100": raw_metrics.get("recall_at_100", 0.0),
            "same_paper_hit_rate": raw_metrics.get("same_paper_hit_rate", 0.0),
        }
        # Also try reading from the more granular baseline_retrieval_quality.json
        detail_path = ROOT / "artifacts" / "benchmarks" / "v2_6_2" / "baseline_retrieval_quality.json"
        if detail_path.exists():
            detail = json.loads(detail_path.read_text())
            ov = detail.get("summary", {}).get("overall", {})
            baseline_metrics.update({
                "paper_hit_rate": ov.get("paper_hit_rate", 0.0),
                "same_section_hit": ov.get("same_section_hit", 0.0),
                "recall_at_10": ov.get("recall_at_10", 0.0),
                "recall_at_100": ov.get("recall_at_100", 0.0),
            })

    results, summary = run_eval(args)

    verdict, gate_results = check_gates(summary)
    print(f"\n[v3.0 Phase 1] Verdict: {verdict}")
    for gate, passed in gate_results.items():
        print(f"  {'✅' if passed else '❌'} {gate}")

    # Save results
    out_json = OUTPUT_DIR / f"phase1_paper_section_recall_{args.stage}.json"
    out_json.write_text(
        json.dumps(
            {
                "version": "v3.0-phase1",
                "stage": args.stage,
                "verdict": verdict,
                "summary": summary,
                "gate_results": gate_results,
                "thresholds": PASS_THRESHOLDS,
                "baseline_metrics": baseline_metrics,
                "results": [asdict(r) for r in results],
            },
            indent=2,
        )
    )
    print(f"\nResults saved: {out_json}")

    # Markdown report
    md_report = build_markdown_report(summary, verdict, gate_results, baseline_metrics, args)
    md_out = OUTPUT_DIR / f"phase1_paper_section_recall_{args.stage}_report.md"
    md_out.write_text(md_report)

    doc_out = DOC_DIR / "v3_0_phase1_report.md"
    doc_out.write_text(md_report)
    print(f"Report saved: {md_out}")
    print(f"Doc report:   {doc_out}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
