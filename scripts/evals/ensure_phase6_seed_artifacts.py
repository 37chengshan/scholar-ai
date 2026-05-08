#!/usr/bin/env python3
"""Create deterministic Phase 6 seed benchmark artifacts for CI release gates.

The benchmark artifact directory is intentionally ignored because real runs can be
large and environment-specific. Release-gate smoke checks still need the frozen
seed shape, so CI bootstraps the smallest deterministic PASS bundle before
running the filesystem-backed eval service tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE6_ROOT = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "phase6"
FAMILIES = [
    "single_fact",
    "method",
    "experiment_result",
    "table",
    "figure_caption",
    "multi_paper_compare",
    "kb_global",
    "no_answer",
]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_corpus() -> dict[str, Any]:
    papers = [
        {
            "paper_id": f"paper_{index:03d}",
            "title": f"ScholarAI Benchmark Paper {index:03d}",
            "topic": FAMILIES[(index - 1) % len(FAMILIES)],
        }
        for index in range(1, 51)
    ]
    queries = [
        {
            "query_id": f"q_{index:03d}",
            "family": FAMILIES[(index - 1) % len(FAMILIES)],
            "question": f"Seed benchmark question {index:03d}",
            "gold_paper_ids": [papers[(index - 1) % len(papers)]["paper_id"]],
            "must_abstain": FAMILIES[(index - 1) % len(FAMILIES)] == "no_answer",
        }
        for index in range(1, 129)
    ]
    return {
        "version": "phase6-v1",
        "dataset_version": "phase6-v1",
        "description": "Deterministic Phase 6 seed corpus for CI release-gate smoke checks.",
        "query_families": FAMILIES,
        "paper_count": len(papers),
        "total_papers": len(papers),
        "query_count": len(queries),
        "total_queries": len(queries),
        "papers": papers,
        "queries": queries,
    }


def run_meta(run_id: str, *, created_at: str, baseline_for: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "git_sha": "ci-seed",
        "dataset_version": "phase6-v1",
        "mode": "offline",
        "reranker": "on",
        "baseline_for": baseline_for,
        "overall_verdict": "PASS",
        "created_at": created_at,
        "query_count": 128,
        "family_counts": {family: 16 for family in FAMILIES},
    }


def dashboard_summary() -> dict[str, Any]:
    return {
        "retrieval_hit_rate": 0.903,
        "top_k_recall": {"recall_at_5": 0.886, "recall_at_10": 0.931},
        "rerank_gain": 0.056,
        "citation_jump_valid_rate": 0.949,
        "answer_supported_rate": 0.879,
        "groundedness": 0.842,
        "abstain_precision": 0.923,
        "fallback_used_count": 2,
        "latency_p50": 1.19,
        "latency_p95": 3.72,
        "cost_per_answer": 0.003,
        "overall_verdict": "PASS",
        "gate_failures": [],
    }


def write_run(run_id: str, *, created_at: str, baseline_for: str) -> dict[str, Any]:
    run_dir = PHASE6_ROOT / "runs" / run_id
    meta = run_meta(run_id, created_at=created_at, baseline_for=baseline_for)
    summary = dashboard_summary()
    write_json(run_dir / "meta.json", meta)
    write_json(run_dir / "dashboard_summary.json", summary)
    write_json(
        run_dir / "retrieval.json",
        {
            "retrieval_hit_rate": summary["retrieval_hit_rate"],
            "recall_at_5": summary["top_k_recall"]["recall_at_5"],
            "recall_at_10": summary["top_k_recall"]["recall_at_10"],
            "by_family": {family: {"recall_at_5": 0.88, "recall_at_10": 0.93} for family in FAMILIES},
        },
    )
    write_json(
        run_dir / "answer_quality.json",
        {
            "answer_supported_rate": summary["answer_supported_rate"],
            "groundedness": summary["groundedness"],
            "abstain_precision": summary["abstain_precision"],
            "by_family": {family: {"answer_supported_rate": 0.87} for family in FAMILIES},
        },
    )
    write_json(
        run_dir / "citation_jump.json",
        {
            "citation_jump_valid_rate": summary["citation_jump_valid_rate"],
            "total_citations_checked": 100,
            "valid_citations": 95,
            "invalid_citations": 5,
            "invalid_reasons": {},
        },
    )
    write_json(run_dir / "diff_from_baseline.json", {"baseline_for": baseline_for, "status": "seed"})
    return meta


def main() -> None:
    baseline = write_run(
        "run_phase6_baseline_001",
        created_at="2026-04-28T00:00:00Z",
        baseline_for="phase6",
    )
    candidate = write_run(
        "run_phase6_candidate_001",
        created_at="2026-04-28T12:00:00Z",
        baseline_for="run_phase6_baseline_001",
    )
    write_json(PHASE6_ROOT / "corpus.json", build_corpus())
    write_json(PHASE6_ROOT / "manifest.json", {"runs": [baseline, candidate]})
    print(f"phase6 seed artifacts ready: {PHASE6_ROOT}")


if __name__ == "__main__":
    main()
