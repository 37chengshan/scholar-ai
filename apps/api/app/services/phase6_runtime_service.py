from __future__ import annotations

from typing import Any, Iterable


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


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
    retrieval_evaluator: dict[str, Any] | None,
    corrective_retrieval_used: bool,
    fallback_used: bool,
    surfaced_recovery: bool,
) -> str:
    if answer_mode == "abstain":
        return "low-confidence"
    if fallback_used and not surfaced_recovery:
        return "low-confidence"
    if unsupported_claim_count > 0 and answer_mode != "full":
        return "low-confidence"
    if answer_mode == "partial":
        return "medium-confidence"
    if (
        degraded
        or unsupported_claim_count > 0
        or bool((retrieval_evaluator or {}).get("is_weak"))
        or corrective_retrieval_used
        or fallback_used
    ):
        return "medium-confidence"
    return "high-confidence"


def _build_raptor_lite_signals(retrieval_diagnostics: dict[str, Any] | None) -> list[str]:
    diagnostics = retrieval_diagnostics or {}
    signals: list[str] = []
    if _coerce_float(diagnostics.get("summary_index_hits")) > 0:
        signals.append("paper_summary_index")
    if _coerce_float(diagnostics.get("section_candidates")) > 0:
        signals.append("section_summary_recall")
    if _coerce_float(diagnostics.get("retrieval_depth_rank")) >= 2.0:
        signals.append("deep_retrieval_plan")
    return _dedupe_strings(signals)


def _build_review_global_evidence(graph_summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(graph_summary, dict):
        return None

    section_seeds = [seed for seed in (graph_summary.get("section_seeds") or []) if isinstance(seed, dict)]
    themes = _dedupe_strings(graph_summary.get("themes"))
    candidate_papers = _dedupe_strings(graph_summary.get("candidate_papers"))
    section_seed_titles = _dedupe_strings(seed.get("title") for seed in section_seeds)
    section_seed_perspectives = _dedupe_strings(seed.get("perspective") for seed in section_seeds)

    if not any(
        [
            bool(graph_summary.get("graph_assist_used")),
            themes,
            candidate_papers,
            section_seed_titles,
        ]
    ):
        return None

    return {
        "graph_assist_used": bool(graph_summary.get("graph_assist_used", False)),
        "storm_lite_used": bool(graph_summary.get("storm_lite_used", False)),
        "themes": themes,
        "candidate_papers": candidate_papers,
        "section_seed_titles": section_seed_titles,
        "section_seed_perspectives": section_seed_perspectives,
        "comparative_section_count": len(section_seeds),
    }


def build_phase6_runtime_contract(
    *,
    answer_mode: str,
    degraded_conditions: Iterable[str] | None = None,
    recovery_actions: list[dict[str, Any]] | None = None,
    truthfulness_report: dict[str, Any] | None = None,
    truthfulness_summary: dict[str, Any] | None = None,
    retrieval_evaluator: dict[str, Any] | None = None,
    retrieval_diagnostics: dict[str, Any] | None = None,
    iterative_actions: list[dict[str, Any]] | None = None,
    fallback_used: bool = False,
    fallback_events: Iterable[str] | None = None,
    recovery_entry: dict[str, Any] | None = None,
    graph_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retrieval_evaluator = retrieval_evaluator or {}
    retrieval_diagnostics = retrieval_diagnostics or {}
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

    corrective_retrieval_used = bool(iterative_actions)
    surfaced_recovery = bool(recovery_actions or next_step_entry)
    raptor_lite_signals = _build_raptor_lite_signals(retrieval_diagnostics)
    review_global_evidence = _build_review_global_evidence(graph_summary)

    confidence_level = _phase6_confidence_level(
        answer_mode=answer_mode,
        degraded=degraded,
        unsupported_claim_count=unsupported_claim_count,
        retrieval_evaluator=retrieval_evaluator,
        corrective_retrieval_used=corrective_retrieval_used,
        fallback_used=fallback_used,
        surfaced_recovery=surfaced_recovery,
    )

    return {
        "answer_mode": answer_mode,
        "confidence_level": confidence_level,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "corrective_retrieval_used": corrective_retrieval_used,
        "corrective_actions": corrective_actions,
        "fallback_used": bool(fallback_used),
        "fallback_events": _dedupe_strings(fallback_events),
        "unsupported_claim_count": unsupported_claim_count,
        "recovery_outcome": recovery_outcome,
        "silent_fallback": bool((fallback_used or degraded) and not recovery_actions and next_step_entry is None),
        "raptor_lite_used": bool(raptor_lite_signals),
        "raptor_lite_signals": raptor_lite_signals,
        "review_global_evidence_used": review_global_evidence is not None,
        "review_global_evidence": review_global_evidence,
        "next_step_entry": next_step_entry,
    }
