#!/usr/bin/env python3
"""Seed baseline/candidate run artifacts for v3.0 academic benchmark."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3_ROOT = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "v3_0_academic"
RUNS = V3_ROOT / "runs"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _summary(*, retrieval: float, recall5: float, recall10: float, citation: float, answer: float, grounded: float, abstain: float, fallback: int, lat95: float, cost: float) -> dict:
    return {
        "retrieval_hit_rate": retrieval,
        "top_k_recall": {"recall_at_5": recall5, "recall_at_10": recall10},
        "rerank_gain": 0.03,
        "citation_jump_valid_rate": citation,
        "answer_supported_rate": answer,
        "groundedness": grounded,
        "abstain_precision": abstain,
        "fallback_used_count": fallback,
        "latency_p50": 1.2,
        "latency_p95": lat95,
        "cost_per_answer": cost,
    }


def _seed_run(
    run_id: str,
    mode: str,
    summary: dict,
    baseline_for: str | None = None,
    mode_parity_with_baseline: bool | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    run_dir = RUNS / run_id

    meta = {
        "run_id": run_id,
        "git_sha": "local-dev",
        "dataset_version": "v3.0-academic-p0",
        "mode": mode,
        "reranker": "on",
        "baseline_for": baseline_for,
        "runtime_truth": {
            "runtime_mode": mode,
            "embedding": {
                "resolved_mode": "shim",
                "provider_name": "tongyi",
                "provider_kind": "deterministic_shim",
                "model": "tongyi-embedding-vision-flash-2026-03-06",
            },
            "vector_store": {
                "resolved_mode": "offline",
                "provider_name": "artifact_index",
            },
            "mode_parity_with_baseline": mode_parity_with_baseline,
        },
        "overall_verdict": "PASS",
        "created_at": now,
        "query_count": 688,
        "family_counts": {
            "fact": 64,
            "method": 64,
            "experiment_result": 64,
            "numeric": 48,
            "table": 48,
            "figure": 48,
            "formula": 32,
            "limitation": 48,
            "compare": 48,
            "cross_paper_synthesis": 48,
            "citation_trace": 32,
            "kb_global": 48,
            "no_answer": 48,
            "conflict_verification": 48,
        },
    }

    _write(run_dir / "meta.json", meta)
    _write(run_dir / "dashboard_summary.json", summary)
    _write(run_dir / "retrieval.json", {
        "retrieval_hit_rate": summary["retrieval_hit_rate"],
        "top_k_recall": summary["top_k_recall"],
        "by_family": {
            "fact": {"recall_at_5": 0.86, "recall_at_10": 0.91},
            "formula": {"recall_at_5": 0.70, "recall_at_10": 0.79},
        },
    })
    _write(run_dir / "evidence.json", {
        "citation_jump_valid_rate": summary["citation_jump_valid_rate"],
        "failure_buckets": {"paper_miss": 12, "section_miss": 18},
    })
    _write(run_dir / "answer_quality.json", {
        "answer_supported_rate": summary["answer_supported_rate"],
        "groundedness": summary["groundedness"],
        "abstain_precision": summary["abstain_precision"],
        "by_family": {
            "compare": {"answer_supported_rate": 0.82, "groundedness": 0.78},
            "formula": {"answer_supported_rate": 0.74, "groundedness": 0.70},
        },
    })
    _write(run_dir / "abstain_quality.json", {
        "abstain_precision": summary["abstain_precision"],
        "false_answer_on_unanswerable": 4,
    })
    _write(run_dir / "family_breakdown.json", {
        "report_only_families": ["formula"],
        "families": {
            "formula": {"hard_gate": False, "score": 0.70},
            "compare": {"hard_gate": True, "score": 0.84},
        },
    })
    _write(run_dir / "domain_breakdown.json", {
        "computer_science": {"retrieval_hit_rate": 0.89},
        "medicine": {"retrieval_hit_rate": 0.86},
        "economics": {"retrieval_hit_rate": 0.87},
        "mathematics": {"retrieval_hit_rate": 0.84},
        "education": {"retrieval_hit_rate": 0.85},
        "interdisciplinary": {"retrieval_hit_rate": 0.83},
    })
    _write(run_dir / "diff_from_baseline.json", {
        "base_run_id": baseline_for,
        "candidate_run_id": run_id,
    })

    return meta


def main() -> int:
    V3_ROOT.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    baseline = _seed_run(
        "run_v3_academic_baseline_001",
        "public_offline",
        _summary(
            retrieval=0.86,
            recall5=0.80,
            recall10=0.88,
            citation=0.90,
            answer=0.83,
            grounded=0.76,
            abstain=0.86,
            fallback=4,
            lat95=4.8,
            cost=0.0031,
        ),
        mode_parity_with_baseline=True,
    )
    candidate = _seed_run(
        "run_v3_academic_candidate_001",
        "public_offline",
        _summary(
            retrieval=0.88,
            recall5=0.82,
            recall10=0.90,
            citation=0.92,
            answer=0.85,
            grounded=0.79,
            abstain=0.88,
            fallback=3,
            lat95=4.4,
            cost=0.0030,
        ),
        baseline_for="run_v3_academic_baseline_001",
        mode_parity_with_baseline=True,
    )

    manifest_path = V3_ROOT / "manifest.json"
    manifest = {"benchmark": "v3_0_academic", "dataset_version": "v3.0-academic-p0", "runs": [baseline, candidate]}
    _write(manifest_path, manifest)

    print(f"seeded manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
