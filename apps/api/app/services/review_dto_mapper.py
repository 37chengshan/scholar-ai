"""DTO mapping for review drafts.

Extracted from review_draft_service.py to keep files under 800 lines.
"""

from __future__ import annotations

from typing import Any

from app.models.review_draft import ReviewDraft, ReviewRun
from app.schemas.review_draft import (
    DraftDoc,
    OutlineDoc,
    ReviewDraftDto,
    ReviewQuality,
)
from app.services.draft_finalizer import derive_known_limitations


def _pick_keys(payload: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k in keys}


_ALLOWED_ERROR_STATES = {
    "insufficient_evidence",
    "graph_unavailable",
    "validation_failed",
    "writer_failed",
    "partial_draft",
}


def to_review_dto(draft: ReviewDraft) -> ReviewDraftDto:
    """Convert a ReviewDraft model to a ReviewDraftDto."""
    outline_payload = draft.outline_doc or {}
    draft_payload = draft.draft_doc or {}
    quality_payload = draft.quality or {}

    safe_outline_sections = []
    for section in outline_payload.get("sections", []) if isinstance(outline_payload, dict) else []:
        if not isinstance(section, dict):
            continue
        safe_outline_sections.append(
            _pick_keys(section, {"title", "intent", "supporting_paper_ids", "seed_evidence"})
        )

    safe_outline = {
        "research_question": (outline_payload.get("research_question") if isinstance(outline_payload, dict) else "") or "",
        "themes": (outline_payload.get("themes") if isinstance(outline_payload, dict) else []) or [],
        "sections": safe_outline_sections,
    }

    safe_draft_sections = []
    for section in draft_payload.get("sections", []) if isinstance(draft_payload, dict) else []:
        if not isinstance(section, dict):
            continue
        safe_paragraphs = []
        for paragraph in section.get("paragraphs", []) if isinstance(section.get("paragraphs"), list) else []:
            if not isinstance(paragraph, dict):
                continue
            safe_paragraphs.append(
                _pick_keys(
                    paragraph,
                    {
                        "paragraph_id",
                        "text",
                        "citations",
                        "evidence_blocks",
                        "claim_verification",
                        "truthfulness_summary",
                        "benchmark_hooks",
                        "citation_coverage_status",
                    },
                )
            )
        safe_draft_sections.append(
            {
                "heading": section.get("heading", ""),
                "paragraphs": safe_paragraphs,
                "omitted_reason": section.get("omitted_reason"),
            }
        )

    safe_draft = {"sections": safe_draft_sections}
    safe_quality = {
        "citation_coverage": quality_payload.get("citation_coverage", 0.0) if isinstance(quality_payload, dict) else 0.0,
        "unsupported_paragraph_rate": quality_payload.get("unsupported_paragraph_rate", 1.0) if isinstance(quality_payload, dict) else 1.0,
        "graph_assist_used": bool(quality_payload.get("graph_assist_used", False)) if isinstance(quality_payload, dict) else False,
        "fallback_used": bool(quality_payload.get("fallback_used", False)) if isinstance(quality_payload, dict) else False,
        "execution_mode": quality_payload.get("execution_mode", "global_review") if isinstance(quality_payload, dict) else "global_review",
        "kernel_profile": quality_payload.get("kernel_profile", "global_kernel") if isinstance(quality_payload, dict) else "global_kernel",
        "storm_lite_used": bool(quality_payload.get("storm_lite_used", False)) if isinstance(quality_payload, dict) else False,
        "adaptive_routing_used": bool(quality_payload.get("adaptive_routing_used", False)) if isinstance(quality_payload, dict) else False,
        "truthfulness_backend": quality_payload.get("truthfulness_backend", "rarr_cove_scifact_lite") if isinstance(quality_payload, dict) else "rarr_cove_scifact_lite",
        "benchmark_hooks": quality_payload.get("benchmark_hooks", {}) if isinstance(quality_payload, dict) else {},
    }
    known_limitations = derive_known_limitations(
        draft_doc=DraftDoc.model_validate(safe_draft),
        quality=ReviewQuality.model_validate(safe_quality),
        error_state=(draft.error_state if draft.error_state in _ALLOWED_ERROR_STATES else None),
        graph_error="graph_unavailable" if draft.error_state == "graph_unavailable" else None,
    )

    return ReviewDraftDto(
        id=draft.id,
        knowledgeBaseId=draft.knowledge_base_id,
        title=draft.title,
        status=draft.status,
        sourcePaperIds=draft.source_paper_ids or [],
        outlineDoc=OutlineDoc.model_validate(safe_outline),
        draftDoc=DraftDoc.model_validate(safe_draft),
        quality=ReviewQuality.model_validate(safe_quality),
        knownLimitations=known_limitations,
        traceId=draft.trace_id or "",
        runId=draft.run_id or "",
        errorState=(draft.error_state if draft.error_state in _ALLOWED_ERROR_STATES else None),
        createdAt=draft.created_at.isoformat() if draft.created_at else "",
        updatedAt=draft.updated_at.isoformat() if draft.updated_at else "",
    )


def to_run_summary(run: ReviewRun) -> dict[str, Any]:
    """Convert a ReviewRun to a summary dict."""
    return {
        "id": run.id,
        "knowledgeBaseId": run.knowledge_base_id,
        "reviewDraftId": run.review_draft_id,
        "status": run.status,
        "scope": run.scope,
        "traceId": run.trace_id or "",
        "errorState": run.error_state,
        "updatedAt": run.updated_at.isoformat() if run.updated_at else "",
        "createdAt": run.created_at.isoformat() if run.created_at else "",
    }


def to_run_detail(run: ReviewRun) -> dict[str, Any]:
    """Convert a ReviewRun to a detailed dict."""
    return {
        "id": run.id,
        "knowledgeBaseId": run.knowledge_base_id,
        "reviewDraftId": run.review_draft_id,
        "status": run.status,
        "scope": run.scope,
        "inputPayload": run.input_payload or {},
        "steps": run.steps or [],
        "toolEvents": run.tool_events or [],
        "artifacts": run.artifacts or [],
        "evidence": run.evidence or [],
        "recoveryActions": run.recovery_actions or [],
        "traceId": run.trace_id or "",
        "errorState": run.error_state,
        "updatedAt": run.updated_at.isoformat() if run.updated_at else "",
        "createdAt": run.created_at.isoformat() if run.created_at else "",
    }
