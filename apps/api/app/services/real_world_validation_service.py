"""Utilities for Phase D real-world validation payload validation and reporting."""

from __future__ import annotations

from collections import Counter
from typing import Any


ALLOWED_SAMPLE_TYPES = {
    "external_import",
    "scan_pdf",
    "figure_heavy",
    "formula_heavy",
    "long_survey",
    "cross_discipline_kb",
    "multilingual",
    "known_failure",
}
ALLOWED_SOURCE_TYPES = {"arxiv", "semantic_scholar", "local_pdf", "other", "mixed"}
ALLOWED_DOCUMENT_COMPLEXITY = {
    "standard",
    "formula_heavy",
    "scan_pdf",
    "figure_heavy",
    "long_survey",
}
ALLOWED_LANGUAGE_MIX = {"en", "zh", "en-zh", "other"}
ALLOWED_RISK = {"low", "medium", "high", "known_failure"}
ALLOWED_STEP_NAMES = {
    "search",
    "import",
    "indexing",
    "read",
    "chat",
    "notes",
    "compare",
    "review",
    "navigation",
}
ALLOWED_STEP_STATUS = {"passed", "failed", "partial", "skipped"}
ALLOWED_SUCCESS_STATES = {"pass", "partial", "blocked"}
ALLOWED_FAILURE_BUCKETS = {"blocking", "degrading", "paper_cut"}
STANDARD_CHAIN = ["search", "import", "read", "chat", "notes", "compare", "review"]
HONESTY_CHECK_KEYS = (
    "metadata_only_honest",
    "fulltext_ready_honest",
    "unsupported_claim_visible",
    "citation_jump_honest",
)


def validate_real_world_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sample_registry = payload.get("sample_registry") or []
    runs = payload.get("runs") or []

    if not isinstance(sample_registry, list):
        return ["sample_registry must be a list"]
    if not isinstance(runs, list):
        return ["runs must be a list"]

    known_sample_ids: set[str] = set()
    for index, sample in enumerate(sample_registry):
        if not isinstance(sample, dict):
            errors.append(f"sample_registry[{index}] must be an object")
            continue
        sample_id = str(sample.get("sample_id") or "").strip()
        if not sample_id:
            errors.append(f"sample_registry[{index}] missing sample_id")
            continue
        if sample_id in known_sample_ids:
            errors.append(f"duplicate sample_id: {sample_id}")
        known_sample_ids.add(sample_id)

        _require_enum(errors, sample, "sample_type", ALLOWED_SAMPLE_TYPES, sample_id)
        _require_enum(errors, sample, "source_type", ALLOWED_SOURCE_TYPES, sample_id)
        _require_enum(errors, sample, "document_complexity", ALLOWED_DOCUMENT_COMPLEXITY, sample_id)
        _require_enum(errors, sample, "language_mix", ALLOWED_LANGUAGE_MIX, sample_id)
        _require_enum(errors, sample, "expected_risk", ALLOWED_RISK, sample_id)

    seen_run_ids: set[str] = set()
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"runs[{index}] must be an object")
            continue

        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            errors.append(f"runs[{index}] missing run_id")
            continue
        if run_id in seen_run_ids:
            errors.append(f"duplicate run_id: {run_id}")
        seen_run_ids.add(run_id)

        success_state = str(run.get("success_state") or "").strip()
        if success_state not in ALLOWED_SUCCESS_STATES:
            errors.append(f"run {run_id} has invalid success_state: {success_state}")

        sample_ids = run.get("sample_ids") or []
        if not isinstance(sample_ids, list) or not sample_ids:
            errors.append(f"run {run_id} must contain non-empty sample_ids")
        else:
            for sample_id in sample_ids:
                if sample_id not in known_sample_ids:
                    errors.append(f"run {run_id} references unknown sample_id: {sample_id}")

        workflow_steps = run.get("workflow_steps") or []
        if not isinstance(workflow_steps, list) or not workflow_steps:
            errors.append(f"run {run_id} must contain workflow_steps")
        else:
            for step in workflow_steps:
                if not isinstance(step, dict):
                    errors.append(f"run {run_id} contains non-object workflow step")
                    continue
                step_name = str(step.get("step_name") or "").strip()
                status = str(step.get("status") or "").strip()
                if step_name not in ALLOWED_STEP_NAMES:
                    errors.append(f"run {run_id} has invalid workflow step: {step_name}")
                if status not in ALLOWED_STEP_STATUS:
                    errors.append(f"run {run_id} has invalid step status for {step_name}: {status}")

        failure_points = run.get("failure_points") or []
        if not isinstance(failure_points, list):
            errors.append(f"run {run_id} failure_points must be a list")
        else:
            for failure in failure_points:
                if not isinstance(failure, dict):
                    errors.append(f"run {run_id} contains non-object failure point")
                    continue
                bucket = str(failure.get("bucket") or "").strip()
                sample_id = str(failure.get("sample_id") or "").strip()
                workflow_step = str(failure.get("workflow_step") or "").strip()
                if bucket not in ALLOWED_FAILURE_BUCKETS:
                    errors.append(f"run {run_id} has invalid failure bucket: {bucket}")
                if sample_id and sample_id not in known_sample_ids:
                    errors.append(f"run {run_id} failure references unknown sample_id: {sample_id}")
                if workflow_step and workflow_step not in ALLOWED_STEP_NAMES:
                    errors.append(
                        f"run {run_id} failure has invalid workflow_step: {workflow_step}"
                    )

        recovery_actions = run.get("recovery_actions")
        if recovery_actions is None:
            errors.append(f"run {run_id} missing recovery_actions")
        elif not isinstance(recovery_actions, list):
            errors.append(f"run {run_id} recovery_actions must be a list")

        evidence_reviews = run.get("evidence_reviews")
        if evidence_reviews is None:
            errors.append(f"run {run_id} missing evidence_reviews")
        elif not isinstance(evidence_reviews, list):
            errors.append(f"run {run_id} evidence_reviews must be a list")

        honesty_checks = run.get("honesty_checks")
        if honesty_checks is None:
            errors.append(f"run {run_id} missing honesty_checks")
        elif not isinstance(honesty_checks, dict):
            errors.append(f"run {run_id} honesty_checks must be an object")

        user_visible_confusions = run.get("user_visible_confusions")
        if user_visible_confusions is None:
            errors.append(f"run {run_id} missing user_visible_confusions")
        elif not isinstance(user_visible_confusions, list):
            errors.append(f"run {run_id} user_visible_confusions must be a list")

    return errors


def summarize_real_world_validation(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_real_world_payload(payload)
    if errors:
        raise ValueError("invalid real-world validation payload: " + "; ".join(errors))

    sample_registry = payload.get("sample_registry") or []
    runs = payload.get("runs") or []

    sample_type_counts = Counter(str(sample.get("sample_type")) for sample in sample_registry)
    risk_counts = Counter(str(sample.get("expected_risk")) for sample in sample_registry)

    success_state_counts = Counter(str(run.get("success_state")) for run in runs)
    step_coverage = Counter()
    step_consumed_counts = Counter()
    full_chain_runs = 0

    bucket_counts = Counter()
    failures_by_step = Counter()
    honesty_affecting_failures = 0

    evidence_review_count = 0
    unsupported_claim_count = 0
    weakly_supported_claim_count = 0
    citation_jump_pass_count = 0

    failed_honesty_checks = Counter({key: 0 for key in HONESTY_CHECK_KEYS})
    run_details: list[dict[str, Any]] = []

    for run in runs:
        run_step_statuses: dict[str, str] = {}
        step_details: list[dict[str, Any]] = []
        for step in run.get("workflow_steps") or []:
            step_name = str(step.get("step_name"))
            status = str(step.get("status"))
            if status == "passed":
                step_coverage[step_name] += 1
            if step.get("consumed_by_next") is True:
                step_consumed_counts[step_name] += 1
            run_step_statuses[step_name] = status
            step_details.append(
                {
                    "step_name": step_name,
                    "status": status,
                    "consumed_by_next": step.get("consumed_by_next") is True,
                    "notes": step.get("notes") or [],
                }
            )
        if all(run_step_statuses.get(step_name) == "passed" for step_name in STANDARD_CHAIN):
            full_chain_runs += 1

        run_failure_points = run.get("failure_points") or []
        for failure in run.get("failure_points") or []:
            bucket = str(failure.get("bucket"))
            workflow_step = str(failure.get("workflow_step") or "unknown")
            bucket_counts[bucket] += 1
            failures_by_step[workflow_step] += 1
            if failure.get("affects_honesty") is True:
                honesty_affecting_failures += 1

        for review in run.get("evidence_reviews") or []:
            evidence_review_count += 1
            unsupported_claim_count += int(review.get("unsupported_claim_count") or 0)
            weakly_supported_claim_count += int(review.get("weakly_supported_claim_count") or 0)
            if review.get("citation_jump_passed") is True:
                citation_jump_pass_count += 1

        honesty_checks = run.get("honesty_checks") or {}
        for key in HONESTY_CHECK_KEYS:
            if honesty_checks.get(key) is False:
                failed_honesty_checks[key] += 1

        run_details.append(
            {
                "run_id": run.get("run_id"),
                "sample_ids": run.get("sample_ids") or [],
                "success_state": run.get("success_state"),
                "runtime_truth": run.get("runtime_truth") or {},
                "step_details": step_details,
                "degraded_conditions": [
                    str(failure.get("description") or "").strip()
                    for failure in run_failure_points
                    if str(failure.get("bucket") or "").strip() in {"degrading", "paper_cut"}
                    and str(failure.get("description") or "").strip()
                ],
                "blocking_conditions": [
                    str(failure.get("description") or "").strip()
                    for failure in run_failure_points
                    if str(failure.get("bucket") or "").strip() == "blocking"
                    and str(failure.get("description") or "").strip()
                ],
                "user_visible_confusions": run.get("user_visible_confusions") or [],
            }
        )

    citation_jump_pass_rate = round(
        citation_jump_pass_count / evidence_review_count, 4
    ) if evidence_review_count else 0.0

    recommendation = _recommendation(
        total_runs=len(runs),
        success_state_counts=success_state_counts,
        bucket_counts=bucket_counts,
        failed_honesty_checks=failed_honesty_checks,
    )

    return {
        "sample_summary": {
            "total_samples": len(sample_registry),
            "sample_type_counts": dict(sample_type_counts),
            "expected_risk_counts": dict(risk_counts),
        },
        "run_summary": {
            "total_runs": len(runs),
            "success_state_counts": dict(success_state_counts),
            "full_chain_runs": full_chain_runs,
        },
        "workflow_summary": {
            "step_pass_counts": dict(step_coverage),
            "step_consumed_counts": dict(step_consumed_counts),
        },
        "failure_summary": {
            "total_failures": sum(bucket_counts.values()),
            "bucket_counts": dict(bucket_counts),
            "failures_by_step": dict(failures_by_step),
            "honesty_affecting_failures": honesty_affecting_failures,
        },
        "evidence_summary": {
            "total_reviews": evidence_review_count,
            "unsupported_claim_count": unsupported_claim_count,
            "weakly_supported_claim_count": weakly_supported_claim_count,
            "citation_jump_pass_rate": citation_jump_pass_rate,
        },
        "honesty_summary": {
            "failed_checks": dict(failed_honesty_checks),
            "total_failed_checks": sum(failed_honesty_checks.values()),
        },
        "recommendation": recommendation,
        "run_details": run_details,
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    sample_summary = summary.get("sample_summary") or {}
    run_summary = summary.get("run_summary") or {}
    workflow_summary = summary.get("workflow_summary") or {}
    failure_summary = summary.get("failure_summary") or {}
    evidence_summary = summary.get("evidence_summary") or {}
    honesty_summary = summary.get("honesty_summary") or {}
    recommendation = summary.get("recommendation") or {}
    run_details = summary.get("run_details") or []

    lines = [
        "# v3.0 Real-world Validation Report",
        "",
        f"- total_samples: {sample_summary.get('total_samples', 0)}",
        f"- total_runs: {run_summary.get('total_runs', 0)}",
        f"- beta_readiness: {recommendation.get('beta_readiness', 'not_ready')}",
        f"- rationale: {recommendation.get('rationale', 'n/a')}",
        "",
        "## 样本组成",
        "",
    ]

    for sample_type, count in sorted((sample_summary.get("sample_type_counts") or {}).items()):
        lines.append(f"- {sample_type}: {count}")
    if not sample_summary.get("sample_type_counts"):
        lines.append("- no samples recorded")

    lines.extend([
        "",
        "## Workflow 覆盖",
        "",
        f"- full_chain_runs: {run_summary.get('full_chain_runs', 0)}",
    ])
    for step_name, count in sorted((workflow_summary.get("step_pass_counts") or {}).items()):
        consumed = (workflow_summary.get("step_consumed_counts") or {}).get(step_name, 0)
        lines.append(f"- {step_name}: passed={count}, consumed_by_next={consumed}")

    lines.extend([
        "",
        "## 本次真实执行链路",
        "",
    ])
    if run_details:
        for run in run_details:
            lines.append(
                f"- {run.get('run_id')}: sample_ids={','.join(run.get('sample_ids') or [])}; success_state={run.get('success_state')}"
            )
            step_parts = [
                f"{step.get('step_name')}={step.get('status')}"
                for step in run.get("step_details") or []
            ]
            if step_parts:
                lines.append(f"  - steps: {' -> '.join(step_parts)}")
            for step in run.get("step_details") or []:
                notes = step.get("notes") or []
                if notes:
                    lines.append(
                        f"  - {step.get('step_name')} notes: {' | '.join(str(note) for note in notes)}"
                    )
            blocking_conditions = run.get("blocking_conditions") or []
            degraded_conditions = run.get("degraded_conditions") or []
            runtime_truth = run.get("runtime_truth") or {}
            if runtime_truth:
                lines.append(f"  - runtime_truth: {runtime_truth}")
            if blocking_conditions:
                lines.append("  - blocking_conditions:")
                for condition in blocking_conditions:
                    lines.append(f"    - {condition}")
            if degraded_conditions:
                lines.append("  - degraded_conditions:")
                for condition in degraded_conditions:
                    lines.append(f"    - {condition}")
            confusions = run.get("user_visible_confusions") or []
            if confusions:
                lines.append("  - user_visible_confusions:")
                for confusion in confusions:
                    lines.append(f"    - {confusion}")
    else:
        lines.append("- no executed runs recorded")

    lines.extend([
        "",
        "## 失败分桶",
        "",
        f"- total_failures: {failure_summary.get('total_failures', 0)}",
    ])
    for bucket, count in sorted((failure_summary.get("bucket_counts") or {}).items()):
        lines.append(f"- {bucket}: {count}")
    if not failure_summary.get("bucket_counts"):
        lines.append("- no failures recorded")

    lines.extend([
        "",
        "## Evidence 质量",
        "",
        f"- total_reviews: {evidence_summary.get('total_reviews', 0)}",
        f"- unsupported_claim_count: {evidence_summary.get('unsupported_claim_count', 0)}",
        f"- weakly_supported_claim_count: {evidence_summary.get('weakly_supported_claim_count', 0)}",
        f"- citation_jump_pass_rate: {evidence_summary.get('citation_jump_pass_rate', 0.0)}",
        "",
        "## Honesty 检查",
        "",
        f"- total_failed_checks: {honesty_summary.get('total_failed_checks', 0)}",
    ])
    for check_name, count in sorted((honesty_summary.get("failed_checks") or {}).items()):
        lines.append(f"- {check_name}: {count}")

    lines.extend([
        "",
        "## Release 建议",
        "",
        f"- beta_readiness: {recommendation.get('beta_readiness', 'not_ready')}",
        f"- rationale: {recommendation.get('rationale', 'n/a')}",
    ])

    next_steps = recommendation.get("next_steps") or []
    if next_steps:
        lines.append("- next_steps:")
        for step in next_steps:
            lines.append(f"  - {step}")

    return "\n".join(lines) + "\n"


def _require_enum(
    errors: list[str],
    payload: dict[str, Any],
    key: str,
    allowed_values: set[str],
    label: str,
) -> None:
    value = str(payload.get(key) or "").strip()
    if value not in allowed_values:
        errors.append(f"sample {label} has invalid {key}: {value}")


def _recommendation(
    *,
    total_runs: int,
    success_state_counts: Counter[str],
    bucket_counts: Counter[str],
    failed_honesty_checks: Counter[str],
) -> dict[str, Any]:
    total_failed_checks = sum(failed_honesty_checks.values())
    blocked_runs = int(success_state_counts.get("blocked", 0))
    blocking_count = int(bucket_counts.get("blocking", 0))
    degrading_count = int(bucket_counts.get("degrading", 0))
    paper_cut_count = int(bucket_counts.get("paper_cut", 0))

    if total_runs == 0:
        return {
            "beta_readiness": "not_ready",
            "rationale": "no real-world runs recorded",
            "next_steps": ["record at least one end-to-end validation run"],
        }
    if blocked_runs > 0 or blocking_count > 0 or total_failed_checks > 0:
        return {
            "beta_readiness": "not_ready",
            "rationale": "blocking failures or honesty regressions remain",
            "next_steps": [
                "fix blocking runs before beta",
                "clear honesty check failures for metadata/fulltext and citation jumps",
            ],
        }
    if degrading_count > 0 or paper_cut_count > 0:
        return {
            "beta_readiness": "conditional",
            "rationale": "workflow passes but degrading or paper-cut issues remain",
            "next_steps": [
                "reduce degrading failures in high-risk samples",
                "capture follow-up fixes for UX paper cuts",
            ],
        }
    return {
        "beta_readiness": "ready",
        "rationale": "no blocking, degrading, or honesty issues recorded",
        "next_steps": ["continue monitoring with additional high-risk samples"],
    }
