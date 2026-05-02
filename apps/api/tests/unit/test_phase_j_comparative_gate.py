from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[4]))

from scripts.evals.run_phase_j_comparative_gate import (
    VERDICT_EXPERIMENT_ONLY,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_WARN,
    compare_runs,
    render_markdown_summary,
    summarize_run,
)


def _entry(
    case_id: str,
    *,
    case_source: str = "academic_public",
    task_family: str = "survey",
    citation_coverage: float = 0.8,
    unsupported_claim_rate: float = 0.1,
    latency_ms: float = 1000.0,
    cost_estimate: float = 0.02,
    degraded_conditions: list[str] | None = None,
    parity: bool = True,
    workflow_success_state: str | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "case_source": case_source,
        "dataset_version": "v3.0-academic-p0" if case_source != "workflow" else "v3.0-d-p0",
        "task_family": task_family,
        "execution_mode": "public_offline" if case_source != "workflow" else "online",
        "truthfulness_report_summary": {
            "unsupported_claim_rate": unsupported_claim_rate,
            "citation_coverage": citation_coverage,
        },
        "retrieval_plane_policy": {"mode": "global_review"},
        "degraded_conditions": degraded_conditions or [],
        "quality": {
            "citation_coverage": citation_coverage,
            "unsupported_claim_rate": unsupported_claim_rate,
        },
        "total_latency_ms": latency_ms,
        "cost_estimate": cost_estimate,
        "runtime_truth": {
            "runtime_mode": "public_offline" if case_source != "workflow" else "online",
            "mode_parity_with_baseline": parity,
        },
        "mode_parity_with_baseline": parity,
        "workflow_success_state": workflow_success_state,
    }


def test_phase_j_comparative_gate_passes_with_complete_hooks_and_improved_metrics() -> None:
    baseline_entries = [_entry("case-1", citation_coverage=0.7, unsupported_claim_rate=0.2)]
    candidate_entries = [_entry("case-1", citation_coverage=0.82, unsupported_claim_rate=0.1, latency_ms=1080.0)]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_PASS
    assert verdict["candidate_missing_hooks"] == 0
    assert verdict["warnings"] == []


def test_phase_j_comparative_gate_fails_when_required_hooks_are_missing() -> None:
    baseline_entries = [_entry("case-1")]
    candidate_entries = [
        {
            "case_id": "case-1",
            "case_source": "academic_public",
            "dataset_version": "v3.0-academic-p0",
            "execution_mode": "public_offline",
            "total_latency_ms": 1000.0,
            "cost_estimate": 0.02,
            "runtime_truth": {"runtime_mode": "public_offline", "mode_parity_with_baseline": True},
            "mode_parity_with_baseline": True,
        }
    ]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_FAIL
    assert "missing_required_hooks" in verdict["failures"]


def test_phase_j_comparative_gate_fails_when_case_sets_do_not_match() -> None:
    baseline_entries = [_entry("case-1")]
    candidate_entries = [_entry("case-2")]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_FAIL
    assert "case_set_mismatch" in verdict["failures"]


def test_phase_j_comparative_gate_marks_mode_parity_mismatch_as_experiment_only() -> None:
    baseline_entries = [_entry("case-1")]
    candidate_entries = [_entry("case-1", parity=False)]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_EXPERIMENT_ONLY
    assert verdict["experiment_reasons"] == ["mode_parity_mismatch"]


def test_phase_j_comparative_gate_warns_on_budget_regressions() -> None:
    baseline_entries = [
        _entry("case-1", latency_ms=1000.0, cost_estimate=0.02),
        _entry("wf-1", case_source="workflow", task_family="Review", workflow_success_state="pass"),
    ]
    candidate_entries = [
        _entry("case-1", latency_ms=1400.0, cost_estimate=0.03),
        _entry("wf-1", case_source="workflow", task_family="Review", workflow_success_state="partial", degraded_conditions=["slow review"]),
    ]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_WARN
    assert "latency_regression" in verdict["warnings"]
    assert "cost_regression" in verdict["warnings"]
    assert "degraded_rate_regression" in verdict["warnings"]


def test_phase_j_comparative_gate_fails_on_citation_or_unsupported_claim_regression() -> None:
    baseline_entries = [_entry("case-1", citation_coverage=0.8, unsupported_claim_rate=0.1)]
    candidate_entries = [_entry("case-1", citation_coverage=0.7, unsupported_claim_rate=0.2)]

    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    assert verdict["verdict"] == VERDICT_FAIL
    assert "citation_coverage_regression" in verdict["failures"]
    assert "unsupported_claim_regression" in verdict["failures"]


def test_render_markdown_summary_includes_closeout_sections() -> None:
    baseline_entries = [_entry("case-1")]
    candidate_entries = [_entry("case-1", degraded_conditions=["slow retrieval"])]
    verdict = compare_runs(
        baseline=summarize_run(baseline_entries),
        candidate=summarize_run(candidate_entries),
    )

    markdown = render_markdown_summary(
        verdict=verdict,
        baseline_label="baseline-run",
        candidate_label="candidate-run",
    )

    assert "# Phase J Comparative Close-out" in markdown
    assert "## Parity" in markdown
    assert "## Metric Deltas" in markdown
    assert "## Per-bucket Diff" in markdown
    assert "## Degraded Conditions" in markdown
