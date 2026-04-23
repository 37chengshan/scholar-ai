#!/usr/bin/env python
"""Summarize 16-run dual-stack benchmark outputs into report tables."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = ROOT / "artifacts" / "benchmarks" / "matrix_runs"
REPORT_PATH = ROOT / "docs" / "reports" / "2026-04-23_retrieval_dual_stack_benchmark_report.md"
STATUS_PATH = RUNS_ROOT / "matrix_status.tsv"

DATASETS = ["large", "xlarge"]
STACKS = ["bge_dual", "qwen_dual"]
RERANK = ["off", "on"]
ROUNDS = ["round1", "round2"]


def _load(dataset: str, stack: str, rerank: str, run_label: str) -> dict:
    path = RUNS_ROOT / dataset / stack / f"{dataset}_{stack}_{rerank}_{run_label}.json"
    if not path.exists():
        return {
            "dataset_label": dataset,
            "model_stack": stack,
            "run_label": run_label,
            "use_reranker": rerank == "on",
            "recall_at_5_avg": 0.0,
            "mrr_avg": 0.0,
            "paper_hit_rate_avg": 0.0,
            "section_hit_rate_avg": 0.0,
            "chunk_hit_rate_avg": 0.0,
            "cross_paper_recall_at_5": 0.0,
            "hard_query_hit_rate": 0.0,
            "latency_avg_ms": 0.0,
            "latency_p95_ms": 0.0,
            "query_details": [],
            "_missing": True,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_missing"] = False
    return payload


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summary(dataset: str, stack: str, rerank: str) -> dict:
    rows = [_load(dataset, stack, rerank, round_label) for round_label in ROUNDS]
    return {
        "r1_recall5": rows[0]["recall_at_5_avg"],
        "r2_recall5": rows[1]["recall_at_5_avg"],
        "avg_recall5": _avg([row["recall_at_5_avg"] for row in rows]),
        "avg_mrr": _avg([row["mrr_avg"] for row in rows]),
        "avg_paper_hit": _avg([row["paper_hit_rate_avg"] for row in rows]),
        "avg_section_hit": _avg([row["section_hit_rate_avg"] for row in rows]),
        "avg_chunk_hit": _avg([row["chunk_hit_rate_avg"] for row in rows]),
        "avg_cross_r5": _avg([row["cross_paper_recall_at_5"] for row in rows]),
        "avg_hard_hit": _avg([row["hard_query_hit_rate"] for row in rows]),
        "avg_latency_ms": _avg([row["latency_avg_ms"] for row in rows]),
        "avg_latency_p95_ms": _avg([row["latency_p95_ms"] for row in rows]),
    }


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def build_report() -> str:
    summary: dict[tuple[str, str, str], dict] = {}
    for dataset in DATASETS:
        for stack in STACKS:
            for rerank in RERANK:
                summary[(dataset, stack, rerank)] = _summary(dataset, stack, rerank)

    lines: list[str] = []
    lines.append("# 2026-04-23 Retrieval Dual Stack Benchmark Report")
    lines.append("")
    if STATUS_PATH.exists():
        lines.append("## Matrix execution status")
        lines.append("")
        lines.append("| dataset | model_stack | reranker | round | status |")
        lines.append("|---|---|---|---|---|")
        for line in STATUS_PATH.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) == 5:
                lines.append(f"| {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} | {parts[4]} |")
        lines.append("")

    lines.append("## Table 1 - 12 papers summary")
    lines.append("")
    lines.append("| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for stack in STACKS:
        for rerank in RERANK:
            s = summary[("large", stack, rerank)]
            lines.append(
                f"| {stack} | {rerank} | {_fmt(s['r1_recall5'])} | {_fmt(s['r2_recall5'])} | {_fmt(s['avg_recall5'])} | {_fmt(s['avg_mrr'])} | {_fmt(s['avg_paper_hit'])} | {_fmt(s['avg_section_hit'])} | {_fmt(s['avg_chunk_hit'])} | {_fmt(s['avg_cross_r5'])} | {_fmt(s['avg_hard_hit'])} | {_fmt(s['avg_latency_ms'])} | {_fmt(s['avg_latency_p95_ms'])} |"
            )
    lines.append("")

    lines.append("## Table 2 - 50 papers summary")
    lines.append("")
    lines.append("| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for stack in STACKS:
        for rerank in RERANK:
            s = summary[("xlarge", stack, rerank)]
            lines.append(
                f"| {stack} | {rerank} | {_fmt(s['r1_recall5'])} | {_fmt(s['r2_recall5'])} | {_fmt(s['avg_recall5'])} | {_fmt(s['avg_mrr'])} | {_fmt(s['avg_paper_hit'])} | {_fmt(s['avg_section_hit'])} | {_fmt(s['avg_chunk_hit'])} | {_fmt(s['avg_cross_r5'])} | {_fmt(s['avg_hard_hit'])} | {_fmt(s['avg_latency_ms'])} | {_fmt(s['avg_latency_p95_ms'])} |"
            )
    lines.append("")

    lines.append("## Table 3 - reranker A/B gain")
    lines.append("")
    lines.append("| dataset | model_stack | metric | reranker_off_avg | reranker_on_avg | delta |")
    lines.append("|---|---|---|---:|---:|---:|")
    metrics = [
        ("avg_recall5", "recall@5"),
        ("avg_section_hit", "section_hit"),
        ("avg_chunk_hit", "chunk_hit"),
        ("avg_cross_r5", "cross_paper_r@5"),
    ]
    for dataset in DATASETS:
        for stack in STACKS:
            off = summary[(dataset, stack, "off")]
            on = summary[(dataset, stack, "on")]
            for metric_key, metric_name in metrics:
                lines.append(
                    f"| {dataset} | {stack} | {metric_name} | {_fmt(off[metric_key])} | {_fmt(on[metric_key])} | {_fmt(on[metric_key] - off[metric_key])} |"
                )
    lines.append("")

    lines.append("## Table 4 - BGE vs Qwen")
    lines.append("")
    lines.append("| dataset | reranker_state | metric | bge_avg | qwen_avg | delta(qwen-bge) |")
    lines.append("|---|---|---|---:|---:|---:|")
    for dataset in DATASETS:
        for rerank in RERANK:
            bge = summary[(dataset, "bge_dual", rerank)]
            qwen = summary[(dataset, "qwen_dual", rerank)]
            for metric_key, metric_name in metrics:
                lines.append(
                    f"| {dataset} | {rerank} | {metric_name} | {_fmt(bge[metric_key])} | {_fmt(qwen[metric_key])} | {_fmt(qwen[metric_key] - bge[metric_key])} |"
                )
    lines.append("")

    lines.append("## Table 5 - failure query classification")
    lines.append("")
    lines.append("| dataset | model_stack | reranker | query_id | query_type | failure_type | possible_cause |")
    lines.append("|---|---|---|---|---|---|---|")
    for dataset in DATASETS:
        for stack in STACKS:
            for rerank in RERANK:
                for round_label in ROUNDS:
                    report = _load(dataset, stack, rerank, round_label)
                    for item in report.get("query_details", []):
                        if item.get("recall_at_5", 0.0) >= 1.0:
                            continue
                        if item.get("section_hit_rate", 0.0) <= 0.0:
                            failure = "section_miss"
                            cause = "section normalization or query mismatch"
                        elif item.get("paper_hit_rate", 0.0) <= 0.0:
                            failure = "paper_miss"
                            cause = "candidate set too narrow"
                        else:
                            failure = "ranking_loss"
                            cause = "rerank or hybrid score ordering"
                        lines.append(
                            f"| {dataset} | {stack} | {rerank} | {item.get('query_id')} | {item.get('query_type', item.get('query_family', 'unknown'))} | {failure} | {cause} |"
                        )

    return "\n".join(lines) + "\n"


def main() -> int:
    content = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8")
    print(str(REPORT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
