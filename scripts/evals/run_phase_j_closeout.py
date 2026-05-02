#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))

from app.services.real_world_validation_service import build_phase_j_workflow_bundle
from scripts.evals.run_phase_j_comparative_gate import run_gate


ARTIFACTS_ROOT = ROOT / "artifacts" / "validation-results" / "phase_j"
ACADEMIC_ROOT = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "v3_0_academic"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _academic_run_bundle(run_id: str, *, role: str) -> dict[str, Any]:
    run_dir = ACADEMIC_ROOT / "runs" / run_id
    meta = _load_json(run_dir / "meta.json")
    summary = _load_json(run_dir / "dashboard_summary.json")
    retrieval = _load_json(run_dir / "retrieval.json")
    answer_quality = _load_json(run_dir / "answer_quality.json")
    family_breakdown = _load_json(run_dir / "family_breakdown.json")
    evidence = _load_json(run_dir / "evidence.json")

    dataset_version = str(meta.get("dataset_version") or "unknown")
    execution_mode = str(meta.get("mode") or "public_offline")
    runtime_truth = meta.get("runtime_truth") if isinstance(meta.get("runtime_truth"), dict) else {}
    if not runtime_truth:
        runtime_truth = {
            "runtime_mode": execution_mode,
            "mode_parity_with_baseline": True,
            "provider_identity": {
                "reported_by": "phase_j_academic_adapter",
                "status": "inferred_from_meta",
            },
        }
    family_counts = meta.get("family_counts") if isinstance(meta.get("family_counts"), dict) else {}

    entries: list[dict[str, Any]] = []
    for family_name, case_count in family_counts.items():
        family_metrics = (
            family_breakdown.get("families", {}).get(family_name)
            if isinstance(family_breakdown.get("families"), dict)
            else {}
        )
        if not isinstance(family_metrics, dict):
            family_metrics = {}
        family_score = float(family_metrics.get("score") or summary.get("answer_supported_rate") or 0.0)
        hard_gate = bool(family_metrics.get("hard_gate")) if isinstance(family_metrics, dict) else False
        case_total = int(case_count or 0)
        if case_total <= 0:
            continue
        unsupported_claim_rate = round(max(0.0, 1.0 - family_score), 4)
        citation_coverage = round(float(summary.get("citation_jump_valid_rate") or 0.0), 4)
        degraded_conditions: list[str] = []
        if not hard_gate:
            degraded_conditions.append("report-only family; not eligible for hard pass on its own")

        entries.append(
            {
                "case_id": family_name,
                "case_source": "academic_public",
                "dataset_version": dataset_version,
                "task_family": family_name,
                "execution_mode": execution_mode,
                "truthfulness_report_summary": {
                    "citation_coverage": citation_coverage,
                    "unsupported_claim_rate": unsupported_claim_rate,
                    "family_score": family_score,
                    "failure_bucket_summary": evidence.get("failure_buckets", {}),
                },
                "retrieval_plane_policy": {
                    "benchmark": "v3_0_academic",
                    "run_id": run_id,
                    "role": role,
                    "reranker": meta.get("reranker"),
                },
                "degraded_conditions": degraded_conditions,
                "citation_coverage": citation_coverage,
                "unsupported_claim_rate": unsupported_claim_rate,
                "total_latency_ms": round(float(summary.get("latency_p95") or 0.0) * 1000.0, 4),
                "cost_estimate": round(float(summary.get("cost_per_answer") or 0.0), 6),
                "runtime_truth": runtime_truth,
                "mode_parity_with_baseline": runtime_truth.get("mode_parity_with_baseline", True),
            }
        )

    return {
        "comparative_bundle_type": "phase_j_academic_bundle",
        "schema_version": "phase_j.academic.v1",
        "benchmark": "v3_0_academic",
        "dataset_version": dataset_version,
        "run_id": run_id,
        "role": role,
        "baseline_run_id": meta.get("baseline_for"),
        "entries": entries,
        "aggregate": {
            "retrieval_hit_rate": retrieval.get("retrieval_hit_rate"),
            "citation_jump_valid_rate": summary.get("citation_jump_valid_rate"),
            "answer_supported_rate": answer_quality.get("answer_supported_rate"),
        },
    }


def _merge_bundles(academic_bundle: dict[str, Any], workflow_bundle: dict[str, Any]) -> dict[str, Any]:
    merged_entries = []
    merged_entries.extend(academic_bundle.get("entries") or [])
    merged_entries.extend(workflow_bundle.get("entries") or [])
    return {
        "comparative_bundle_type": "phase_j_merged_bundle",
        "schema_version": "phase_j.bundle.v1",
        "dataset_version": academic_bundle.get("dataset_version"),
        "academic": {
            "run_id": academic_bundle.get("run_id"),
            "role": academic_bundle.get("role"),
        },
        "workflow": {
            "dataset_version": workflow_bundle.get("dataset_version"),
        },
        "entries": merged_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase J orchestration close-out")
    parser.add_argument("--academic-baseline-run", required=True)
    parser.add_argument("--academic-candidate-run", required=True)
    parser.add_argument("--workflow-baseline", required=True, help="Baseline workflow raw JSON payload")
    parser.add_argument("--workflow-candidate", required=True, help="Candidate workflow raw JSON payload")
    parser.add_argument("--output-dir", default=str(ARTIFACTS_ROOT / "latest"))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    academic_baseline_bundle = _academic_run_bundle(args.academic_baseline_run, role="baseline")
    academic_candidate_bundle = _academic_run_bundle(args.academic_candidate_run, role="candidate")
    workflow_baseline_bundle = build_phase_j_workflow_bundle(_load_json(Path(args.workflow_baseline)))
    workflow_candidate_bundle = build_phase_j_workflow_bundle(_load_json(Path(args.workflow_candidate)))

    merged_baseline = _merge_bundles(academic_baseline_bundle, workflow_baseline_bundle)
    merged_candidate = _merge_bundles(academic_candidate_bundle, workflow_candidate_bundle)

    verdict = run_gate(
        baseline_payload=merged_baseline,
        candidate_payload=merged_candidate,
        baseline_label=args.academic_baseline_run,
        candidate_label=args.academic_candidate_run,
    )

    _write_json(output_dir / "academic_baseline.bundle.json", academic_baseline_bundle)
    _write_json(output_dir / "academic_candidate.bundle.json", academic_candidate_bundle)
    _write_json(output_dir / "workflow_baseline.bundle.json", workflow_baseline_bundle)
    _write_json(output_dir / "workflow_candidate.bundle.json", workflow_candidate_bundle)
    _write_json(output_dir / "baseline.bundle.json", merged_baseline)
    _write_json(output_dir / "candidate.bundle.json", merged_candidate)
    _write_json(output_dir / "comparative_verdict.json", verdict)
    _write_json(output_dir / "comparative_diff.json", verdict.get("per_bucket_diff") or {})
    (output_dir / "closeout_summary.md").write_text(verdict.get("markdown_summary") or "", encoding="utf-8")

    print(json.dumps(
        {
            "output_dir": str(output_dir),
            "verdict": verdict.get("verdict"),
            "recommendation": verdict.get("recommendation"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
