from __future__ import annotations

from typing import Any, Iterable


def _dedupe_strings(values: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values or []:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _truthfulness_unsupported_count(
    *,
    truthfulness_report: dict[str, Any] | None,
    truthfulness_summary: dict[str, Any] | None,
) -> int:
    if isinstance(truthfulness_summary, dict):
        value = truthfulness_summary.get("unsupported_claims")
        if value is not None:
            return int(value or 0)
    if isinstance(truthfulness_report, dict):
        value = truthfulness_report.get("unsupportedClaimCount")
        if value is not None:
            return int(value or 0)
        results = truthfulness_report.get("results")
        if isinstance(results, list):
            return sum(1 for item in results if str(item.get("support_level") or "") == "unsupported")
    return 0


def _phase6_confidence_level(
    *,
    answer_mode: str,
    degraded: bool,
    unsupported_claim_count: int,
) -> str:
    if answer_mode == "abstain":
        return "low-confidence"
    if answer_mode == "partial":
        return "medium-confidence"
    if degraded or unsupported_claim_count > 0:
        return "medium-confidence"
    return "high-confidence"


def build_phase6_runtime_contract(
    *,
    answer_mode: str,
    degraded_conditions: Iterable[str] | None = None,
    recovery_actions: list[dict[str, Any]] | None = None,
    truthfulness_report: dict[str, Any] | None = None,
    truthfulness_summary: dict[str, Any] | None = None,
    retrieval_evaluator: dict[str, Any] | None = None,
    iterative_actions: list[dict[str, Any]] | None = None,
    fallback_used: bool = False,
    fallback_events: Iterable[str] | None = None,
    recovery_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retrieval_evaluator = retrieval_evaluator or {}
    recovery_actions = list(recovery_actions or [])
    weak_reasons = _dedupe_strings(retrieval_evaluator.get("weak_reasons"))
    degraded_reasons = _dedupe_strings(degraded_conditions)

    if retrieval_evaluator.get("is_weak"):
        degraded_reasons.extend(
            reason for reason in [*weak_reasons, "weak_first_pass_retrieval"]
            if reason not in degraded_reasons
        )
    if iterative_actions:
        degraded_reasons.append("corrective_retrieval_triggered")
    if fallback_used:
        degraded_reasons.append("fallback_used")

    unsupported_claim_count = _truthfulness_unsupported_count(
        truthfulness_report=truthfulness_report,
        truthfulness_summary=truthfulness_summary,
    )
    if unsupported_claim_count > 0 and "claim_verification_failed" not in degraded_reasons:
        degraded_reasons.append("claim_verification_failed")

    if answer_mode == "partial" and "partial_answer" not in degraded_reasons:
        degraded_reasons.append("partial_answer")
    if answer_mode == "abstain" and "insufficient_evidence" not in degraded_reasons:
        degraded_reasons.append("insufficient_evidence")

    degraded_reasons = _dedupe_strings(degraded_reasons)
    corrective_actions = _dedupe_strings(action.get("action") for action in recovery_actions)
    degraded = bool(
        degraded_reasons
        or fallback_used
        or retrieval_evaluator.get("is_weak")
        or answer_mode in {"partial", "abstain"}
    )

    if not degraded:
        recovery_outcome = "not_needed"
    elif answer_mode == "full":
        recovery_outcome = "recovered"
    elif answer_mode == "partial":
        recovery_outcome = "partial"
    else:
        recovery_outcome = "failed"

    next_step_entry = None
    for action in recovery_actions:
        if str(action.get("action") or "") == "open_recovery_entry":
            params = action.get("params")
            if isinstance(params, dict):
                next_step_entry = params
                break
    if next_step_entry is None and isinstance(recovery_entry, dict):
        next_step_entry = recovery_entry

    confidence_level = _phase6_confidence_level(
        answer_mode=answer_mode,
        degraded=degraded,
        unsupported_claim_count=unsupported_claim_count,
    )

    return {
        "answer_mode": answer_mode,
        "confidence_level": confidence_level,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "corrective_retrieval_used": bool(iterative_actions),
        "corrective_actions": corrective_actions,
        "fallback_used": bool(fallback_used),
        "fallback_events": _dedupe_strings(fallback_events),
        "unsupported_claim_count": unsupported_claim_count,
        "recovery_outcome": recovery_outcome,
        "silent_fallback": bool(degraded and not recovery_actions and not degraded_reasons),
        "next_step_entry": next_step_entry,
    }
