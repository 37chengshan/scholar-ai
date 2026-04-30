from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[4]))

from scripts.evals.run_phase_j_comparative_gate import compare_runs, summarize_run


def test_phase_j_comparative_gate_passes_with_complete_hooks_and_better_truthfulness() -> None:
    baseline_entries = [
        {
            "case_id": "case-1",
            "task_family": "survey",
            "execution_mode": "global_review",
            "truthfulness_report_summary": {
                "unsupported_claim_rate": 0.2,
                "citation_coverage": 0.7,
            },
            "retrieval_plane_policy": {"mode": "global_review"},
            "degraded_conditions": [],
            "quality": {"citation_coverage": 0.7, "unsupported_claim_rate": 0.2},
            "trace": {"total_latency_ms": 1200.0},
            "cost_estimate": 0.02,
        }
    ]
    candidate_entries = [
        {
            "case_id": "case-1",
            "task_family": "survey",
            "execution_mode": "global_review",
            "truthfulness_report_summary": {
                "unsupported_claim_rate": 0.1,
                "citation_coverage": 0.82,
            },
            "retrieval_plane_policy": {"mode": "global_review", "review_strategy": "storm_lite"},
            "degraded_conditions": [],
            "quality": {"citation_coverage": 0.82, "unsupported_claim_rate": 0.1},
            "trace": {"total_latency_ms": 1260.0},
            "cost_estimate": 0.021,
        }
    ]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["pass"] is True
    assert verdict["candidate_missing_hooks"] == 0


def test_phase_j_comparative_gate_fails_when_required_hooks_are_missing() -> None:
    baseline_entries = [
        {
            "case_id": "case-1",
            "task_family": "survey",
            "execution_mode": "global_review",
            "truthfulness_report_summary": {"unsupported_claim_rate": 0.1, "citation_coverage": 0.8},
            "retrieval_plane_policy": {"mode": "global_review"},
            "degraded_conditions": [],
            "quality": {"citation_coverage": 0.8, "unsupported_claim_rate": 0.1},
            "trace": {"total_latency_ms": 1000.0},
            "cost_estimate": 0.02,
        }
    ]
    candidate_entries = [
        {
            "case_id": "case-1",
            "execution_mode": "global_review",
            "quality": {"citation_coverage": 0.78, "unsupported_claim_rate": 0.18},
            "trace": {"total_latency_ms": 1000.0},
            "cost_estimate": 0.02,
        }
    ]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["pass"] is False
    assert verdict["candidate_missing_hooks"] > 0


def test_phase_j_comparative_gate_fails_when_case_sets_do_not_match() -> None:
    baseline_entries = [
        {
            "case_id": "case-1",
            "task_family": "survey",
            "execution_mode": "global_review",
            "truthfulness_report_summary": {"unsupported_claim_rate": 0.1, "citation_coverage": 0.8},
            "retrieval_plane_policy": {"mode": "global_review"},
            "degraded_conditions": [],
            "quality": {"citation_coverage": 0.8, "unsupported_claim_rate": 0.1},
            "trace": {"total_latency_ms": 1000.0},
            "cost_estimate": 0.02,
        }
    ]
    candidate_entries = [
        {
            "case_id": "case-2",
            "task_family": "survey",
            "execution_mode": "global_review",
            "truthfulness_report_summary": {"unsupported_claim_rate": 0.09, "citation_coverage": 0.81},
            "retrieval_plane_policy": {"mode": "global_review"},
            "degraded_conditions": [],
            "quality": {"citation_coverage": 0.81, "unsupported_claim_rate": 0.09},
            "trace": {"total_latency_ms": 1000.0},
            "cost_estimate": 0.02,
        }
    ]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["pass"] is False
    assert "case_set_mismatch" in verdict["failures"]