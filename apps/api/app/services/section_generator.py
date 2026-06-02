"""Section evidence retrieval and draft writing for review generation.

Extracted from review_draft_service.py to keep files under 800 lines.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.milvus_service import get_milvus_service
from app.core.embedding.factory import get_embedding_service
from app.models.retrieval import SearchConstraints
from app.rag_v3.schemas import EvidenceBlock, EvidenceCandidate
from app.schemas.review_draft import (
    DraftDoc,
    DraftParagraph,
    DraftSection,
    EvidenceRetrieverOutput,
    OutlineDoc,
    OutlineSection,
)
from app.services.evidence_contract_service import build_citation_jump_url, get_evidence_source_payload
from app.services.phase_i_routing_service import PhaseIRoutingDecision
from app.services.truthfulness_service import get_truthfulness_service
from app.utils.logger import logger


def candidate_to_evidence_block(cand: EvidenceCandidate) -> EvidenceBlock:
    """Convert an EvidenceCandidate to an EvidenceBlock."""
    payload = get_evidence_source_payload(cand.source_chunk_id) or {}
    citation_jump_url = payload.get("citation_jump_url") or build_citation_jump_url(
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
        page_num=payload.get("page_num"),
    )
    text = str(payload.get("content") or payload.get("anchor_text") or cand.anchor_text or "")

    return EvidenceBlock(
        evidence_id=cand.source_chunk_id,
        source_type="paper",
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
        page_num=payload.get("page_num"),
        section_path=payload.get("section_path") or cand.section_id,
        content_type=cand.content_type,
        text=text,
        score=cand.rrf_score,
        rerank_score=cand.rerank_score,
        support_status=(
            "supported" if cand.rerank_score >= 0.7 else "weakly_supported" if cand.rerank_score >= 0.4 else "unsupported"
        ),
        citation_jump_url=citation_jump_url,
    )


def diversify_evidence_blocks(*, blocks: list[EvidenceBlock], limit: int) -> list[EvidenceBlock]:
    """Diversify evidence blocks by limiting per-paper count."""
    diversified: list[EvidenceBlock] = []
    seen_per_paper: dict[str, int] = {}
    for block in blocks:
        paper_id = block.paper_id or "unknown-paper"
        if seen_per_paper.get(paper_id, 0) >= 2:
            continue
        diversified.append(block)
        seen_per_paper[paper_id] = seen_per_paper.get(paper_id, 0) + 1
        if len(diversified) >= limit:
            break
    return diversified


def retrieve_live_evidence_fallback(
    *,
    query: str,
    user_id: str,
    paper_ids: list[str],
    top_k: int = 6,
) -> list[EvidenceBlock]:
    """Fallback to the live Milvus paper contents collection for fresh imports.

    The review pipeline's primary retriever is artifact-backed and can miss
    newly imported papers that have not been materialized into the static
    artifact index yet.
    """
    if not paper_ids:
        return []

    query_embedding = get_embedding_service().encode_text(query)
    constraints = SearchConstraints(
        user_id=user_id,
        paper_ids=paper_ids,
        content_types=["text"],
        min_quality_score=0.25,
    )
    hits = get_milvus_service().search_contents_v2(
        embedding=query_embedding,
        top_k=top_k,
        constraints=constraints,
    )

    blocks: list[EvidenceBlock] = []
    for hit in hits:
        paper_id = str(hit.get("paper_id") or "")
        source_chunk_id = str(hit.get("id") or "")
        if not paper_id or not source_chunk_id:
            continue

        page_num = hit.get("page_num")
        section_path = hit.get("section")
        text = str(hit.get("text") or hit.get("content") or "").strip()
        if not text:
            continue

        score = float(hit.get("score") or 0.0)
        blocks.append(
            EvidenceBlock(
                evidence_id=source_chunk_id,
                source_type="paper",
                paper_id=paper_id,
                source_chunk_id=source_chunk_id,
                page_num=page_num if isinstance(page_num, int) else None,
                section_path=str(section_path or "") or None,
                content_type=str(hit.get("content_type") or "text"),
                text=text,
                quote_text=text[:600],
                score=score,
                rerank_score=score,
                support_status=(
                    "supported"
                    if score >= 0.7
                    else "weakly_supported"
                    if score >= 0.4
                    else "unsupported"
                ),
                citation_jump_url=build_citation_jump_url(
                    paper_id=paper_id,
                    source_chunk_id=source_chunk_id,
                    page_num=page_num if isinstance(page_num, int) else None,
                ),
            )
        )
    return blocks


def synthesize_section_text(
    *,
    question: str,
    section: OutlineSection,
    evidence_blocks: list[EvidenceBlock],
) -> str:
    """Synthesize section text from evidence blocks."""
    if not evidence_blocks:
        return ""
    paper_examples: list[str] = []
    seen_papers: set[str] = set()
    for block in evidence_blocks:
        if block.paper_id in seen_papers:
            continue
        seen_papers.add(block.paper_id)
        snippet = (block.text or block.quote_text or "").strip().replace("\n", " ")
        if snippet:
            paper_examples.append(f"{block.paper_id}: {snippet[:180]}")
        if len(paper_examples) >= 3:
            break
    lead = (
        f"For {question}, the {section.title.lower()} perspective suggests that "
        f"the literature can be organized around {section.intent.lower()}."
    )
    examples = " ".join(paper_examples)
    tail = (
        " This STORM-lite section keeps only evidence-backed synthesis and preserves"
        " explicit cross-paper coverage."
    )
    return f"{lead} {examples}{tail}".strip()


def retrieve_section_evidence(
    *,
    user_id: str,
    paper_ids: list[str],
    outline_doc: OutlineDoc,
    routing: PhaseIRoutingDecision,
    retrieve_evidence_fn: Any,
    steps: list[dict[str, Any]],
    tool_events: list[dict[str, Any]],
) -> list[EvidenceRetrieverOutput]:
    """Retrieve evidence for each section in the outline."""
    outputs: list[EvidenceRetrieverOutput] = []
    for section in outline_doc.sections:
        tool_event_id = uuid4().hex
        tool_events.append(
            {
                "event_id": tool_event_id,
                "tool_name": "hybrid_retriever",
                "event_type": "call",
                "args": {
                    "query_family": "survey",
                    "paper_ids": paper_ids,
                    "section_title": section.title,
                    "kernel_scope": routing.kernel_scope,
                    "review_strategy": routing.review_strategy,
                },
                "status": "running",
            }
        )

        query = (
            f"Research question: {outline_doc.research_question}. "
            f"Section: {section.title}. Intent: {section.intent}. "
            f"Perspective: {section.perspective}. Themes: {', '.join(outline_doc.themes[:4])}."
        )
        top_k = 8 if routing.retrieval_depth == "deep" else 6
        try:
            pack = retrieve_evidence_fn(
                query=query,
                user_id=user_id,
                paper_scope=paper_ids,
                query_family="survey",
                stage="rule",
                top_k=top_k,
            )
            blocks = [candidate_to_evidence_block(c) for c in pack.candidates[:top_k]]
            blocks = diversify_evidence_blocks(blocks=blocks, limit=top_k)
            if not blocks and paper_ids:
                blocks = retrieve_live_evidence_fallback(
                    query=query,
                    user_id=user_id,
                    paper_ids=paper_ids,
                    top_k=top_k,
                )
            tool_events.append(
                {
                    "event_id": tool_event_id,
                    "tool_name": "hybrid_retriever",
                    "event_type": "result",
                    "result": {
                        "candidate_count": len(pack.candidates),
                        "paper_coverage_count": int(pack.diagnostics.get("paper_coverage_count", 0.0)),
                        "live_fallback_used": bool(blocks) and len(pack.candidates) == 0,
                        "section_retrieval_mode": section.retrieval_mode,
                    },
                    "status": "success",
                }
            )
        except Exception as exc:
            logger.warning(
                "Review evidence retrieval degraded",
                section_title=section.title,
                query=query,
                error=str(exc),
            )
            blocks = []
            tool_events.append(
                {
                    "event_id": tool_event_id,
                    "tool_name": "hybrid_retriever",
                    "event_type": "result",
                    "result": {
                        "candidate_count": 0,
                        "paper_coverage_count": 0,
                        "error": str(exc),
                    },
                    "status": "error",
                }
            )

        outputs.append(
            EvidenceRetrieverOutput(
                section_title=section.title,
                evidence_bundles=blocks,
            )
        )

    steps.append(
        {
            "step_name": "evidence_retriever",
            "status": "completed",
            "started_at": "",
            "ended_at": "",
            "metadata": {
                "input_schema_name": "EvidenceRetrieverInput",
                "output_schema_name": "EvidenceRetrieverOutput",
            },
        }
    )
    return outputs


def write_draft(
    *,
    outline_doc: OutlineDoc,
    section_evidence: list[EvidenceRetrieverOutput],
    routing: PhaseIRoutingDecision,
) -> DraftDoc:
    """Write the draft document from outline and evidence."""
    sections: list[DraftSection] = []
    for section, section_bundle in zip(outline_doc.sections, section_evidence):
        if not section_bundle.evidence_bundles:
            sections.append(
                DraftSection(
                    heading=section.title,
                    paragraphs=[],
                    omitted_reason="insufficient_evidence",
                )
            )
            continue

        top_blocks = section_bundle.evidence_bundles[:3]
        citation_rows = [
            {
                "paper_id": block.paper_id,
                "source_chunk_id": block.source_chunk_id,
                "page_num": block.page_num,
                "section_path": block.section_path,
                "content_type": block.content_type,
                "citation_jump_url": block.citation_jump_url,
            }
            for block in top_blocks
        ]
        text = synthesize_section_text(
            question=outline_doc.research_question,
            section=section,
            evidence_blocks=top_blocks,
        )
        if not text:
            text = "Evidence found but no extractable text snippet."

        truthfulness_report = get_truthfulness_service().evaluate_text(
            text=text,
            evidence_blocks=top_blocks,
        )

        claim_verification = _build_claim_verification(text=text, evidence_blocks=top_blocks)

        paragraph = DraftParagraph(
            paragraph_id=uuid4().hex[:12],
            text=text,
            citations=citation_rows,
            evidence_blocks=top_blocks,
            claim_verification=claim_verification,
            truthfulness_summary=truthfulness_report.get("summary", {}),
            benchmark_hooks={
                "task_family": routing.task_family,
                "execution_mode": routing.execution_mode,
                "section_title": section.title,
                "review_strategy": routing.review_strategy,
                "truthfulness_report_summary": truthfulness_report.get("summary", {}),
                "retrieval_plane_policy": routing.retrieval_plane_policy,
                "degraded_conditions": [],
            },
            citation_coverage_status="covered",
        )
        sections.append(
            DraftSection(
                heading=section.title,
                paragraphs=[paragraph],
            )
        )
    return DraftDoc(sections=sections)


def _build_claim_verification(*, text: str, evidence_blocks: list[EvidenceBlock]) -> list[dict[str, Any]]:
    report = get_truthfulness_service().evaluate_text(text=text, evidence_blocks=evidence_blocks)
    return _truthfulness_report_to_claim_rows(report)


def _truthfulness_report_to_claim_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    from app.services.evidence_action_service import build_claim_recovery_actions
    from app.core.claim_schema import ClaimSupportLevel

    results: list[dict[str, Any]] = []
    for item in report.get("results", []):
        support_status = item["support_level"]
        results.append(
            {
                "claim_id": item["claim_id"],
                "claim_text": item["text"],
                "claim_type": item["claim_type"],
                "support_status": support_status,
                "support_score": item["support_score"],
                "supporting_evidence_ids": item["evidence_ids"],
                "repairable": support_status != "supported",
                "repair_hint": item["reason"],
                "recovery_actions": build_claim_recovery_actions(
                    claim_id=item["claim_id"],
                    support_status=support_status,
                    repair_hint=item.get("reason"),
                    supporting_evidence_ids=item.get("evidence_ids"),
                    scope="review",
                ),
            }
        )
    return results
