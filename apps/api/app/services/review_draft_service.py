"""Phase 5 ReviewDraft service.

Implements a practical global-local review pipeline:
- outline_planner
- evidence_retriever
- review_writer
- citation_validator
- draft_finalizer
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.milvus_service import get_milvus_service
from app.core.neo4j_service import Neo4jService
from app.core.embedding.factory import get_embedding_service
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
from app.models.retrieval import SearchConstraints
from app.models.review_draft import ReviewDraft, ReviewRun
from app.rag_v3.main_path_service import retrieve_evidence as retrieve_review_evidence
from app.rag_v3.schemas import EvidenceBlock, EvidenceCandidate
from app.schemas.review_draft import (
    CitationValidatorOutput,
    DraftDoc,
    DraftFinalizerInput,
    DraftParagraph,
    DraftSection,
    EvidenceRetrieverOutput,
    OutlineDoc,
    OutlineSection,
    ReviewDraftDto,
    ReviewQuality,
)
from app.services.evidence_contract_service import build_citation_jump_url, get_evidence_source_payload
from app.services.phase_i_routing_service import PhaseIRoutingDecision, get_phase_i_routing_service
from app.services.evidence_action_service import build_claim_recovery_actions
from app.services.phase6_runtime_service import build_phase6_runtime_contract
from app.services.truthfulness_service import get_truthfulness_service
from app.utils.logger import logger

from app.services.outline_planner import (
    global_discovery,
    build_outline,
    derive_themes_from_titles,
    is_graph_available,
)
from app.services.section_generator import (
    retrieve_section_evidence,
    write_draft,
    candidate_to_evidence_block,
    diversify_evidence_blocks,
    retrieve_live_evidence_fallback,
    synthesize_section_text,
)
from app.services.draft_finalizer import (
    validate_draft,
    finalize_draft,
    derive_known_limitations,
    build_graph_global_evidence,
    merge_claim_rows,
    build_truthfulness_summary,
)
from app.services.review_dto_mapper import (
    to_review_dto as _to_review_dto,
    to_run_summary as _to_run_summary,
    to_run_detail as _to_run_detail,
)

_ALLOWED_ERROR_STATES = {
    "insufficient_evidence",
    "graph_unavailable",
    "validation_failed",
    "writer_failed",
    "partial_draft",
}

_ARTIFACT_TYPES = (
    "review_draft",
    "citation_audit",
    "evidence_note",
    "compare_matrix",
    "graph_global_synthesis",
    "known_limitations",
    "run_trace",
)


def _pick_keys(payload: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k in keys}


def _build_run_artifact(
    *,
    artifact_id: str,
    run_id: str,
    artifact_type: str,
    title: str,
    content: Optional[str] = None,
    url: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if artifact_type not in _ARTIFACT_TYPES:
        artifact_type = "run_trace"
    return {
        "artifact_id": artifact_id,
        "run_id": run_id,
        "type": artifact_type,
        "title": title,
        "content": content,
        "url": url,
        "metadata": metadata or {},
    }


def _first_evidence_block(draft_doc: DraftDoc) -> Optional[EvidenceBlock]:
    for section in draft_doc.sections:
        for paragraph in section.paragraphs:
            if paragraph.evidence_blocks:
                return paragraph.evidence_blocks[0]
    return None


class ReviewDraftService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieve_evidence = retrieve_review_evidence

    async def create_or_regenerate(
        self,
        *,
        kb_id: str,
        user_id: str,
        mode: str,
        paper_ids: Optional[list[str]] = None,
        question: Optional[str] = None,
        target_review_draft_id: Optional[str] = None,
        is_retry: bool = False,
    ) -> ReviewDraft:
        if mode != "outline_and_draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mode must be 'outline_and_draft'",
            )

        kb = await self._get_kb(kb_id=kb_id, user_id=user_id)
        selected_papers = await self._resolve_source_papers(
            kb_id=kb_id,
            user_id=user_id,
            paper_ids=paper_ids,
        )

        if not selected_papers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="knowledge base has no papers to review",
            )

        source_paper_ids = [paper.id for paper in selected_papers]
        review_question = question or "Synthesize related work trends and key differences."
        routing = get_phase_i_routing_service().route(
            query=review_question,
            query_family="survey",
            paper_scope=source_paper_ids,
        )

        draft = await self._get_or_create_draft(
            kb_id=kb_id,
            user_id=user_id,
            source_paper_ids=source_paper_ids,
            question=review_question,
            target_review_draft_id=target_review_draft_id,
        )

        run = ReviewRun(
            knowledge_base_id=kb_id,
            user_id=user_id,
            review_draft_id=draft.id,
            status="running",
            scope="subset" if paper_ids else "full_kb",
            input_payload={
                "paper_ids": source_paper_ids,
                "question": review_question,
                "mode": mode,
                "is_retry": is_retry,
            },
            steps=[],
            tool_events=[],
            artifacts=[],
            evidence=[],
            recovery_actions=[],
            trace_id=uuid4().hex,
        )
        self.db.add(run)
        await self.db.flush()

        draft.status = "running"
        draft.run_id = run.id
        draft.trace_id = run.trace_id
        draft.error_state = None
        draft.updated_at = datetime.now(timezone.utc)

        steps: list[dict[str, Any]] = []
        tool_events: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        evidence_rows: list[dict[str, Any]] = []

        try:
            graph_summary, graph_error = await global_discovery(
                kb_enable_graph=kb.enable_graph,
                papers=selected_papers,
                question=review_question,
                routing=routing,
            )
            graph_global_evidence = build_graph_global_evidence(
                graph_summary=graph_summary,
                graph_error=graph_error,
                routing=routing,
            )
            if graph_global_evidence:
                artifacts.append(
                    _build_run_artifact(
                        artifact_id=f"{run.id}:graph_global_synthesis",
                        run_id=run.id,
                        artifact_type="graph_global_synthesis",
                        title="Review Graph Global Synthesis",
                        metadata=graph_global_evidence,
                    )
                )
            steps.append(
                self._step(
                    step_name="outline_planner",
                    input_schema_name="OutlinePlannerInput",
                    output_schema_name="OutlinePlannerOutput",
                    status="completed",
                )
            )

            outline_doc = build_outline(
                papers=selected_papers,
                question=review_question,
                graph_summary=graph_summary,
                routing=routing,
            )
            artifacts.append(
                _build_run_artifact(
                    artifact_id=f"{run.id}:review_draft:outline",
                    run_id=run.id,
                    artifact_type="review_draft",
                    title="Review Draft Outline",
                    metadata={
                        "section_count": len(outline_doc.sections),
                        "paper_ids": source_paper_ids,
                    },
                )
            )

            section_evidence = retrieve_section_evidence(
                user_id=user_id,
                paper_ids=source_paper_ids,
                outline_doc=outline_doc,
                routing=routing,
                retrieve_evidence_fn=self._retrieve_evidence,
                steps=steps,
                tool_events=tool_events,
            )

            draft_doc = write_draft(
                outline_doc=outline_doc,
                section_evidence=section_evidence,
                routing=routing,
            )
            steps.append(
                self._step(
                    step_name="review_writer",
                    input_schema_name="ReviewWriterInput",
                    output_schema_name="ReviewWriterOutput",
                    status="completed",
                )
            )

            validated_doc, coverage_report = validate_draft(draft_doc)
            steps.append(
                self._step(
                    step_name="citation_validator",
                    input_schema_name="CitationValidatorInput",
                    output_schema_name="CitationValidatorOutput",
                    status="completed",
                )
            )

            finalizer_input = DraftFinalizerInput(
                draft_doc=validated_doc,
                coverage_report=coverage_report,
                run_metadata={
                    "run_id": run.id,
                    "trace_id": run.trace_id,
                    "graph_summary": graph_summary,
                    "graph_error": graph_error,
                },
            )
            final_doc, quality, error_state = finalize_draft(
                finalizer_input=finalizer_input,
                graph_used=bool(graph_summary.get("graph_assist_used", False)),
                graph_error=graph_error,
                routing=routing,
            )
            steps.append(
                self._step(
                    step_name="draft_finalizer",
                    input_schema_name="DraftFinalizerInput",
                    output_schema_name="DraftFinalizerOutput",
                    status="completed",
                )
            )

            for sec in final_doc.sections:
                for p in sec.paragraphs:
                    for ev in p.evidence_blocks:
                        evidence_rows.append(ev.model_dump())

            citation_audit_rows = [
                {
                    "section": section.heading,
                    "paragraph_id": paragraph.paragraph_id,
                    "coverage_status": paragraph.citation_coverage_status,
                    "claim_count": len(paragraph.claim_verification or []),
                }
                for section in final_doc.sections
                for paragraph in section.paragraphs
            ]
            known_limitations = derive_known_limitations(
                draft_doc=final_doc,
                quality=quality,
                error_state=error_state,
                graph_error=graph_error,
            )
            first_evidence_block = _first_evidence_block(final_doc)
            compare_url = (
                f"/compare?paper_ids={','.join(source_paper_ids)}"
                if len(source_paper_ids) >= 2
                else None
            )
            evidence_note_url = None
            evidence_note_metadata: dict[str, Any] = {"available": False}
            if first_evidence_block:
                evidence_note_url = (
                    f"/notes?paperId={first_evidence_block.paper_id}"
                    f"&sourceChunkId={first_evidence_block.source_chunk_id}"
                )
                evidence_note_metadata = {
                    "available": True,
                    "paper_id": first_evidence_block.paper_id,
                    "source_chunk_id": first_evidence_block.source_chunk_id,
                    "page_num": first_evidence_block.page_num,
                    "section_path": first_evidence_block.section_path,
                    "citation_jump_url": first_evidence_block.citation_jump_url,
                }
            artifacts.extend(
                [
                    _build_run_artifact(
                        artifact_id=f"{run.id}:citation_audit",
                        run_id=run.id,
                        artifact_type="citation_audit",
                        title="Citation Audit",
                        metadata={"rows": citation_audit_rows},
                    ),
                    _build_run_artifact(
                        artifact_id=f"{run.id}:evidence_note",
                        run_id=run.id,
                        artifact_type="evidence_note",
                        title="Evidence Note",
                        url=evidence_note_url,
                        metadata=evidence_note_metadata,
                    ),
                    _build_run_artifact(
                        artifact_id=f"{run.id}:compare_matrix",
                        run_id=run.id,
                        artifact_type="compare_matrix",
                        title="Compare Matrix",
                        url=compare_url,
                        metadata={
                            "paper_ids": source_paper_ids,
                            "available": bool(compare_url),
                        },
                    ),
                    _build_run_artifact(
                        artifact_id=f"{run.id}:known_limitations",
                        run_id=run.id,
                        artifact_type="known_limitations",
                        title="Known Limitations",
                        content="\n".join(f"- {item}" for item in known_limitations),
                        metadata={"items": known_limitations},
                    ),
                    _build_run_artifact(
                        artifact_id=f"{run.id}:run_trace",
                        run_id=run.id,
                        artifact_type="run_trace",
                        title="Run Trace",
                        metadata={
                            "step_count": len(steps),
                            "tool_event_count": len(tool_events),
                            "evidence_count": len(evidence_rows),
                            "recovery_action_count": 1 if error_state else 0,
                        },
                    ),
                ]
            )

            draft.outline_doc = outline_doc.model_dump(mode="json")
            draft.draft_doc = final_doc.model_dump(mode="json")
            draft.quality = quality.model_dump(mode="json")
            draft.error_state = error_state
            if error_state in {"partial_draft", "insufficient_evidence", "graph_unavailable", "validation_failed"}:
                draft.status = "partial"
            elif error_state == "writer_failed":
                draft.status = "failed"
            else:
                draft.status = "completed"
            draft.updated_at = datetime.now(timezone.utc)

            run.status = "completed"
            run.steps = steps
            run.tool_events = tool_events
            run.artifacts = artifacts
            run.evidence = evidence_rows
            run.error_state = error_state
            run.recovery_actions = list(quality.benchmark_hooks.get("phase6_runtime", {}).get("recovery_actions") or [])
            run.tool_events = tool_events + [
                {
                    "event_id": uuid4().hex,
                    "tool_name": "phase_j_hook",
                    "event_type": "result",
                    "result": quality.benchmark_hooks,
                    "status": "success",
                }
            ]
            run.updated_at = datetime.now(timezone.utc)

            await self.db.flush()
            return draft

        except HTTPException:
            run.status = "failed"
            run.error_state = "writer_failed"
            run.steps = steps + [
                self._step(
                    step_name="draft_finalizer",
                    input_schema_name="DraftFinalizerInput",
                    output_schema_name="DraftFinalizerOutput",
                    status="failed",
                )
            ]
            run.recovery_actions = [{"action": "retry", "reason": "writer_failed"}]
            draft.status = "failed"
            draft.error_state = "writer_failed"
            draft.updated_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise
        except Exception as exc:
            run.status = "failed"
            run.error_state = "writer_failed"
            run.recovery_actions = [{"action": "retry", "reason": "writer_failed"}]
            draft.status = "failed"
            draft.error_state = "writer_failed"
            draft.updated_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="review generation failed",
            )

    async def list_drafts(self, *, kb_id: str, user_id: str, limit: int, offset: int) -> tuple[list[ReviewDraft], int]:
        await self._get_kb(kb_id=kb_id, user_id=user_id)
        all_rows = await self.db.execute(
            select(ReviewDraft)
            .where(
                ReviewDraft.knowledge_base_id == kb_id,
                ReviewDraft.user_id == user_id,
            )
            .order_by(ReviewDraft.updated_at.desc())
        )
        rows = all_rows.scalars().all()
        total = len(rows)
        return rows[offset: offset + limit], total

    async def get_draft(self, *, kb_id: str, draft_id: str, user_id: str) -> ReviewDraft:
        row = await self.db.execute(
            select(ReviewDraft).where(
                ReviewDraft.id == draft_id,
                ReviewDraft.knowledge_base_id == kb_id,
                ReviewDraft.user_id == user_id,
            )
        )
        draft = row.scalar_one_or_none()
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review draft not found")
        return draft

    async def retry_draft(self, *, kb_id: str, draft_id: str, user_id: str) -> ReviewDraft:
        draft = await self.get_draft(kb_id=kb_id, draft_id=draft_id, user_id=user_id)
        return await self.create_or_regenerate(
            kb_id=kb_id,
            user_id=user_id,
            mode="outline_and_draft",
            paper_ids=draft.source_paper_ids,
            question=draft.question,
            target_review_draft_id=draft.id,
            is_retry=True,
        )

    async def repair_claim(
        self,
        *,
        kb_id: str,
        draft_id: str,
        paragraph_id: str,
        claim_id: str,
        user_id: str,
    ) -> ReviewDraft:
        draft = await self.get_draft(kb_id=kb_id, draft_id=draft_id, user_id=user_id)
        payload = draft.draft_doc or {}
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft payload invalid")

        for section in payload.get("sections", []) if isinstance(payload.get("sections"), list) else []:
            if not isinstance(section, dict):
                continue
            paragraphs = section.get("paragraphs")
            if not isinstance(paragraphs, list):
                continue
            for paragraph in paragraphs:
                if not isinstance(paragraph, dict):
                    continue
                if str(paragraph.get("paragraph_id") or "") != paragraph_id:
                    continue

                claims = paragraph.get("claim_verification")
                claim_rows = claims if isinstance(claims, list) else []
                target_claim = None
                for item in claim_rows:
                    if isinstance(item, dict) and str(item.get("claim_id") or "") == claim_id:
                        target_claim = item
                        break
                if target_claim is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="claim not found")

                claim_text = str(target_claim.get("claim_text") or target_claim.get("claim") or "").strip()
                if not claim_text:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="claim text missing")

                claim_type = str(target_claim.get("claim_type") or "factual")
                evidence_blocks = paragraph.get("evidence_blocks")
                typed_blocks: list[EvidenceBlock] = []
                for block in evidence_blocks if isinstance(evidence_blocks, list) else []:
                    if not isinstance(block, dict):
                        continue
                    typed_blocks.append(
                        EvidenceBlock(
                            evidence_id=str(block.get("evidence_id") or block.get("source_chunk_id") or "unknown"),
                            paper_id=str(block.get("paper_id") or "unknown-paper"),
                            source_chunk_id=str(block.get("source_chunk_id") or block.get("evidence_id") or "unknown"),
                            text=str(block.get("text") or block.get("quote_text") or ""),
                            quote_text=str(block.get("quote_text") or ""),
                            content_type=str(block.get("content_type") or "text"),
                            citation_jump_url=str(block.get("citation_jump_url") or ""),
                        )
                    )

                result = get_truthfulness_service().repair_claim(
                    claim_text=claim_text,
                    claim_id=claim_id,
                    claim_type=claim_type,
                    evidence_blocks=typed_blocks,
                )
                target_claim.update(
                    {
                        "claim_id": claim_id,
                        "claim_text": claim_text,
                        "claim_type": claim_type,
                        "support_status": result["support_level"],
                        "support_score": result["support_score"],
                        "supporting_evidence_ids": result["evidence_ids"],
                        "repairable": result["repairable"],
                        "repair_hint": result["repair_hint"],
                    }
                )
                refreshed_report = get_truthfulness_service().evaluate_text(
                    text=str(paragraph.get("text") or ""),
                    evidence_blocks=typed_blocks,
                )
                refreshed_rows = self._truthfulness_report_to_claim_rows(refreshed_report)
                merged_rows = merge_claim_rows(
                    refreshed_rows=refreshed_rows,
                    repaired_claim={
                        "claim_id": claim_id,
                        "claim_text": claim_text,
                        "claim_type": claim_type,
                        "support_status": result["support_level"],
                        "support_score": result["support_score"],
                        "supporting_evidence_ids": result["evidence_ids"],
                        "repairable": result["repairable"],
                        "repair_hint": result["repair_hint"],
                    },
                )
                paragraph["truthfulness_summary"] = build_truthfulness_summary(
                    claim_rows=merged_rows,
                    verifier_backend=str(
                        refreshed_report.get("summary", {}).get("verifier_backend")
                        or refreshed_report.get("verifierBackend")
                        or "rarr_cove_scifact_lite"
                    ),
                )
                paragraph["claim_verification"] = merged_rows

                draft.draft_doc = copy.deepcopy(payload)
                draft.updated_at = datetime.now(timezone.utc)
                await self.db.flush()
                await self.db.commit()
                await self.db.refresh(draft)
                return draft

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="paragraph not found")

    async def list_runs(self, *, kb_id: str, user_id: str, limit: int, offset: int) -> tuple[list[ReviewRun], int]:
        await self._get_kb(kb_id=kb_id, user_id=user_id)
        all_rows = await self.db.execute(
            select(ReviewRun)
            .where(
                ReviewRun.knowledge_base_id == kb_id,
                ReviewRun.user_id == user_id,
            )
            .order_by(ReviewRun.updated_at.desc())
        )
        rows = all_rows.scalars().all()
        total = len(rows)
        return rows[offset: offset + limit], total

    async def get_run(self, *, run_id: str, user_id: str) -> ReviewRun:
        row = await self.db.execute(
            select(ReviewRun).where(
                ReviewRun.id == run_id,
                ReviewRun.user_id == user_id,
            )
        )
        run = row.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
        return run

    @staticmethod
    def to_review_dto(draft: ReviewDraft) -> ReviewDraftDto:
        return _to_review_dto(draft)

    # -----------------------------
    # Internal helpers
    # -----------------------------

    async def _get_kb(self, *, kb_id: str, user_id: str) -> KnowledgeBase:
        kb_row = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id,
            )
        )
        kb = kb_row.scalar_one_or_none()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge base not found")
        return kb

    async def _resolve_source_papers(
        self,
        *,
        kb_id: str,
        user_id: str,
        paper_ids: Optional[list[str]],
    ) -> list[Paper]:
        q = select(Paper).where(
            Paper.knowledge_base_id == kb_id,
            Paper.user_id == user_id,
        )
        if paper_ids:
            q = q.where(Paper.id.in_(paper_ids))
        result = await self.db.execute(q)
        papers = result.scalars().all()
        if paper_ids and len(papers) != len(set(paper_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="some paper_ids are not in this knowledge base",
            )
        return papers

    async def _get_or_create_draft(
        self,
        *,
        kb_id: str,
        user_id: str,
        source_paper_ids: list[str],
        question: str,
        target_review_draft_id: Optional[str],
    ) -> ReviewDraft:
        if target_review_draft_id:
            existing = await self.get_draft(
                kb_id=kb_id,
                draft_id=target_review_draft_id,
                user_id=user_id,
            )
            existing.source_paper_ids = source_paper_ids
            existing.question = question
            existing.title = existing.title or "Related Work Draft"
            return existing

        draft = ReviewDraft(
            knowledge_base_id=kb_id,
            user_id=user_id,
            title="Related Work Draft",
            status="idle",
            source_paper_ids=source_paper_ids,
            question=question,
            outline_doc={"research_question": question, "themes": [], "sections": []},
            draft_doc={"sections": []},
            quality={
                "citation_coverage": 0.0,
                "unsupported_paragraph_rate": 1.0,
                "graph_assist_used": False,
                "fallback_used": False,
            },
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    @staticmethod
    def _step(
        *,
        step_name: str,
        input_schema_name: str,
        output_schema_name: str,
        status: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "step_name": step_name,
            "status": status,
            "started_at": now,
            "ended_at": now,
            "metadata": {
                "input_schema_name": input_schema_name,
                "output_schema_name": output_schema_name,
            },
        }

    @staticmethod
    def to_run_summary(run: ReviewRun) -> dict[str, Any]:
        return _to_run_summary(run)

    @staticmethod
    def to_run_detail(run: ReviewRun) -> dict[str, Any]:
        return _to_run_detail(run)
