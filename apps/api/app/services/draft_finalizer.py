"""Draft finalization, validation, and quality assessment for review generation.

Extracted from review_draft_service.py to keep files under 800 lines.
"""

from __future__ import annotations

from typing import Any, Optional

from app.schemas.review_draft import (
    CitationValidatorOutput,
    DraftDoc,
    DraftParagraph,
    DraftSection,
    ReviewQuality,
)
from app.services.phase_i_routing_service import PhaseIRoutingDecision
from app.services.phase6_runtime_service import build_phase6_runtime_contract


def validate_draft(draft_doc: DraftDoc) -> tuple[DraftDoc, list[CitationValidatorOutput]]:
    """Validate draft document and generate coverage report."""
    validated_sections: list[DraftSection] = []
    coverage_report: list[CitationValidatorOutput] = []

    for section in draft_doc.sections:
        kept: list[DraftParagraph] = []
        for paragraph in section.paragraphs:
            has_citations = len(paragraph.citations) > 0
            has_evidence = len(paragraph.evidence_blocks) > 0
            if has_citations and has_evidence:
                paragraph.citation_coverage_status = "covered"
                kept.append(paragraph)
                coverage_report.append(CitationValidatorOutput(coverage_status="covered", issues=[]))
            else:
                coverage_report.append(CitationValidatorOutput(coverage_status="insufficient", issues=["missing citation or evidence"]))

        if not kept:
            validated_sections.append(
                DraftSection(
                    heading=section.heading,
                    paragraphs=[],
                    omitted_reason=section.omitted_reason or "insufficient_evidence",
                )
            )
        else:
            validated_sections.append(
                DraftSection(
                    heading=section.heading,
                    paragraphs=kept,
                    omitted_reason=None,
                )
            )

    return DraftDoc(sections=validated_sections), coverage_report


def finalize_draft(
    *,
    finalizer_input: Any,
    graph_used: bool,
    graph_error: Optional[str],
    routing: PhaseIRoutingDecision,
) -> tuple[DraftDoc, ReviewQuality, Optional[str]]:
    """Finalize the draft document with quality metrics."""
    draft_doc = finalizer_input.draft_doc
    total = 0
    covered = 0
    omitted_sections = 0
    for section in draft_doc.sections:
        if section.omitted_reason:
            omitted_sections += 1
        for p in section.paragraphs:
            total += 1
            if p.citation_coverage_status == "covered":
                covered += 1

    citation_coverage = covered / max(total, 1)
    unsupported_rate = (total - covered) / max(total, 1)

    fallback_used = graph_error is not None
    error_state: Optional[str] = None

    if total == 0:
        error_state = "insufficient_evidence"
    elif omitted_sections > 0:
        error_state = "partial_draft"
    if graph_error == "graph_unavailable" and error_state is None:
        error_state = "partial_draft"

    graph_summary = finalizer_input.run_metadata.get("graph_summary") if isinstance(finalizer_input.run_metadata, dict) else {}
    graph_global_evidence = build_graph_global_evidence(
        graph_summary=graph_summary if isinstance(graph_summary, dict) else {},
        graph_error=graph_error,
        routing=routing,
    )
    resolved_execution_mode = "local_evidence" if graph_error == "graph_unavailable" else routing.execution_mode

    truthfulness_summary = {
        "unsupported_claim_rate": round(unsupported_rate, 4),
        "citation_coverage": round(citation_coverage, 4),
        "verifier_backend": routing.verification_backend,
        "answer_mode": "abstain" if total == 0 else ("partial" if error_state == "partial_draft" else "full"),
        "unsupported_claims": total - covered,
    }
    recovery_actions = (
        [{"action": "retry", "reason": error_state}] if error_state
        else []
    )
    phase6_runtime = build_phase6_runtime_contract(
        answer_mode=truthfulness_summary["answer_mode"],
        degraded_conditions=[graph_error] if graph_error else ([error_state] if error_state else []),
        recovery_actions=recovery_actions,
        truthfulness_summary=truthfulness_summary,
        retrieval_evaluator=None,
        retrieval_diagnostics=None,
        iterative_actions=None,
        fallback_used=fallback_used,
        fallback_events=[graph_error] if graph_error else [],
        recovery_entry={
            "task_family": routing.task_family,
            "entry_type": "review",
        },
        graph_summary=graph_summary if isinstance(graph_summary, dict) else None,
    )

    quality = ReviewQuality(
        citation_coverage=citation_coverage,
        unsupported_paragraph_rate=unsupported_rate,
        graph_assist_used=graph_used,
        fallback_used=fallback_used,
        execution_mode=resolved_execution_mode,
        kernel_profile=routing.kernel_scope,
        storm_lite_used=routing.review_strategy == "storm_lite",
        adaptive_routing_used=routing.retrieval_plane_policy.get("routing_policy") == "adaptive_depth",
        truthfulness_backend=routing.verification_backend,
        benchmark_hooks={
            "task_family": routing.task_family,
            "execution_mode": resolved_execution_mode,
            "truthfulness_report_summary": truthfulness_summary,
            "retrieval_plane_policy": routing.retrieval_plane_policy,
            "degraded_conditions": [graph_error] if graph_error else [],
            "graph_global_evidence": graph_global_evidence,
            "phase6_runtime": {
                **phase6_runtime,
                "recovery_actions": recovery_actions,
            },
        },
    )
    return draft_doc, quality, error_state


def derive_known_limitations(
    *,
    draft_doc: DraftDoc,
    quality: ReviewQuality,
    error_state: Optional[str],
    graph_error: Optional[str],
) -> list[str]:
    """Derive known limitations from draft quality metrics."""
    limitations: list[str] = []
    if quality.citation_coverage < 1.0:
        limitations.append("部分段落仍需要更强证据支撑")
    if quality.unsupported_paragraph_rate > 0.0:
        limitations.append("存在未完全支撑的论断，需要继续修复")
    if error_state == "partial_draft":
        limitations.append("当前草稿为部分完成状态，不能视为全文闭环")
    if error_state == "insufficient_evidence":
        limitations.append("可用证据不足，部分章节被省略")
    if graph_error == "graph_unavailable":
        limitations.append("图增强不可用，已降级为 local-only 生成")
    if not limitations and any(section.omitted_reason for section in draft_doc.sections):
        limitations.append("存在被省略的章节，需要继续补充证据")
    if not limitations:
        limitations.append("当前草稿无显著已知限制")
    return limitations


def build_graph_global_evidence(
    *,
    graph_summary: dict[str, Any] | None,
    graph_error: Optional[str],
    routing: PhaseIRoutingDecision,
) -> dict[str, Any]:
    """Build graph global evidence metadata."""
    payload = graph_summary or {}
    section_seeds = [seed for seed in (payload.get("section_seeds") or []) if isinstance(seed, dict)]
    resolved_execution_mode = "local_evidence" if graph_error == "graph_unavailable" else routing.execution_mode

    def _dedupe(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    return {
        "graph_assist_used": bool(payload.get("graph_assist_used", False)),
        "graph_error": graph_error,
        "themes": _dedupe([str(item).strip() for item in (payload.get("themes") or [])]),
        "candidate_papers": _dedupe([str(item).strip() for item in (payload.get("candidate_papers") or [])]),
        "section_seed_titles": _dedupe([str(seed.get("title") or "").strip() for seed in section_seeds]),
        "section_seed_perspectives": _dedupe([str(seed.get("perspective") or "").strip() for seed in section_seeds]),
        "comparative_section_count": len(section_seeds),
        "storm_lite_used": bool(payload.get("storm_lite_used", False)),
        "execution_mode": resolved_execution_mode,
    }


def merge_claim_rows(
    *,
    refreshed_rows: list[dict[str, Any]],
    repaired_claim: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge refreshed claim rows with a repaired claim."""
    merged_rows: list[dict[str, Any]] = []
    repaired_claim_id = str(repaired_claim.get("claim_id") or "")
    replaced = False

    for row in refreshed_rows:
        if str(row.get("claim_id") or "") == repaired_claim_id:
            merged_rows.append(repaired_claim)
            replaced = True
        else:
            merged_rows.append(row)

    if not replaced:
        merged_rows.append(repaired_claim)
    return merged_rows


def build_truthfulness_summary(
    *,
    claim_rows: list[dict[str, Any]],
    verifier_backend: str,
) -> dict[str, Any]:
    """Build truthfulness summary from claim rows."""
    total_claims = len(claim_rows)
    supported_claims = sum(1 for row in claim_rows if row.get("support_status") == "supported")
    weakly_supported_claims = sum(
        1 for row in claim_rows if row.get("support_status") == "weakly_supported"
    )
    partially_supported_claims = sum(
        1 for row in claim_rows if row.get("support_status") == "partially_supported"
    )
    unsupported_claims = sum(1 for row in claim_rows if row.get("support_status") == "unsupported")

    if total_claims == 0:
        answer_mode = "abstain"
    elif unsupported_claims > 0 or supported_claims == 0:
        answer_mode = "abstain"
    elif supported_claims == total_claims:
        answer_mode = "full"
    else:
        answer_mode = "partial"

    return {
        "total_claims": total_claims,
        "supported_claims": supported_claims,
        "weakly_supported_claims": weakly_supported_claims,
        "partially_supported_claims": partially_supported_claims,
        "unsupported_claims": unsupported_claims,
        "answer_mode": answer_mode,
        "verifier_backend": verifier_backend,
    }
