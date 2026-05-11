from __future__ import annotations

from typing import Any, Iterable


def _claim_targets_from_report(
    truthfulness_report: dict[str, Any] | None,
    *,
    support_levels: set[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for item in (truthfulness_report or {}).get("results", []):
        support_level = str(item.get("support_level") or "")
        if support_level not in support_levels:
            continue
        targets.append(
            {
                "claim_id": str(item.get("claim_id") or ""),
                "text": str(item.get("text") or ""),
                "support_level": support_level,
                "evidence_ids": list(item.get("evidence_ids") or []),
                "repair_hint": str(item.get("reason") or ""),
            }
        )
        if len(targets) >= limit:
            break
    return targets


def build_claim_recovery_actions(
    *,
    claim_id: str,
    support_status: str,
    repair_hint: str | None,
    supporting_evidence_ids: Iterable[str] | None = None,
    scope: str,
) -> list[dict[str, Any]]:
    if support_status == "supported":
        return []

    evidence_ids = [str(item) for item in (supporting_evidence_ids or []) if str(item)]
    return [
        {
            "action": "repair_claim",
            "status": "recommended" if support_status == "unsupported" else "available",
            "scope": scope,
            "reason": repair_hint or "claim needs stronger evidence before reuse",
            "params": {
                "claim_id": claim_id,
                "support_status": support_status,
                "supporting_evidence_ids": evidence_ids[:3],
            },
        }
    ]


def build_recovery_actions(
    *,
    scope: str,
    answer_mode: str,
    task_family: str,
    execution_mode: str,
    retrieval_evaluator: dict[str, Any] | None = None,
    iterative_actions: list[dict[str, Any]] | None = None,
    truthfulness_report: dict[str, Any] | None = None,
    degraded_conditions: list[str] | None = None,
    recovery_entry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    retrieval_evaluator = retrieval_evaluator or {}
    weak_reasons = list(retrieval_evaluator.get("weak_reasons") or [])
    if retrieval_evaluator.get("is_weak"):
        actions.append(
            {
                "action": "continue_retrieval",
                "status": "recommended",
                "scope": scope,
                "reason": "first-pass retrieval was too weak for reliable synthesis",
                "params": {
                    "task_family": task_family,
                    "execution_mode": execution_mode,
                    "weak_reasons": weak_reasons,
                },
            }
        )

    for item in iterative_actions or []:
        action_name = str(item.get("action") or "")
        if action_name == "query_rewrite":
            actions.append(
                {
                    "action": "rewrite_query",
                    "status": "available",
                    "scope": scope,
                    "reason": "rewrite query and retry retrieval with a narrower academic intent",
                    "params": {
                        "queries": list(item.get("queries") or []),
                    },
                }
            )
        elif action_name == "citation_expansion":
            actions.append(
                {
                    "action": "expand_scope",
                    "status": "available",
                    "scope": scope,
                    "reason": "expand citation neighborhood before final synthesis",
                    "params": {
                        "query_family": item.get("query_family"),
                    },
                }
            )
        elif action_name == "summary_fallback":
            actions.append(
                {
                    "action": "degrade_to_summary",
                    "status": "available",
                    "scope": scope,
                    "reason": "fallback to summary evidence when direct support is still weak",
                    "params": {
                        "query": item.get("query"),
                    },
                }
            )

    unsupported_targets = _claim_targets_from_report(
        truthfulness_report,
        support_levels={"unsupported"},
    )
    weak_targets = _claim_targets_from_report(
        truthfulness_report,
        support_levels={"weakly_supported", "partially_supported"},
    )
    if unsupported_targets or weak_targets:
        targets = unsupported_targets or weak_targets
        actions.append(
            {
                "action": "verify_claim",
                "status": "recommended" if unsupported_targets else "available",
                "scope": scope,
                "reason": "review claim-level support before reusing the answer",
                "params": {
                    "claim_ids": [item["claim_id"] for item in targets if item["claim_id"]],
                    "support_levels": [item["support_level"] for item in targets],
                },
            }
        )
        actions.append(
            {
                "action": "repair_claim",
                "status": "recommended" if unsupported_targets else "available",
                "scope": scope,
                "reason": "unsupported or weakly supported claims need citation repair",
                "params": {
                    "targets": targets,
                },
            }
        )

    if answer_mode == "partial":
        actions.append(
            {
                "action": "repair_citation",
                "status": "available",
                "scope": scope,
                "reason": "partial answers should be tightened before downstream reuse",
                "params": {
                    "task_family": task_family,
                },
            }
        )
    elif answer_mode == "abstain":
        actions.append(
            {
                "action": "open_recovery_entry",
                "status": "recommended",
                "scope": scope,
                "reason": "answer abstained because current evidence is not strong enough",
                "params": recovery_entry
                or {
                    "task_family": task_family,
                    "entry_type": scope,
                },
            }
        )

    if degraded_conditions:
        actions.append(
            {
                "action": "review_degraded_conditions",
                "status": "required",
                "scope": scope,
                "reason": "the runtime already degraded or fell back during this answer path",
                "params": {
                    "degraded_conditions": list(degraded_conditions),
                },
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for action in actions:
        key = (str(action.get("action") or ""), str(action.get("reason") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(action)
    return deduped
