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
from app.services.truthfulness_service import get_truthfulness_service
from app.utils.logger import logger

_ALLOWED_ERROR_STATES = {
    "insufficient_evidence",
    "graph_unavailable",
    "validation_failed",
    "writer_failed",
    "partial_draft",
}


def _pick_keys(payload: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k in keys}


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
            graph_summary, graph_error = await self._global_discovery(
                kb=kb,
                papers=selected_papers,
                question=review_question,
                routing=routing,
            )
            steps.append(
                self._step(
                    step_name="outline_planner",
                    input_schema_name="OutlinePlannerInput",
                    output_schema_name="OutlinePlannerOutput",
                    status="completed",
                )
            )

            outline_doc = self._build_outline(
                papers=selected_papers,
                question=review_question,
                graph_summary=graph_summary,
                routing=routing,
            )
            artifacts.append({"type": "outline", "section_count": len(outline_doc.sections)})

            section_evidence = self._retrieve_section_evidence(
                user_id=user_id,
                paper_ids=source_paper_ids,
                outline_doc=outline_doc,
                routing=routing,
                steps=steps,
                tool_events=tool_events,
            )

            draft_doc = self._write_draft(
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

            validated_doc, coverage_report = self._validate_draft(draft_doc)
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
                },
            )
            final_doc, quality, error_state = self._finalize(
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
            run.recovery_actions = (
                [{"action": "retry", "reason": error_state}] if error_state else []
            )
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
                merged_rows = self._merge_claim_rows(
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
                paragraph["truthfulness_summary"] = self._build_truthfulness_summary(
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

        return ReviewDraftDto(
            id=draft.id,
            knowledgeBaseId=draft.knowledge_base_id,
            title=draft.title,
            status=draft.status,  # type: ignore[arg-type]
            sourcePaperIds=draft.source_paper_ids or [],
            outlineDoc=OutlineDoc.model_validate(safe_outline),
            draftDoc=DraftDoc.model_validate(safe_draft),
            quality=ReviewQuality.model_validate(safe_quality),
            traceId=draft.trace_id or "",
            runId=draft.run_id or "",
            errorState=(draft.error_state if draft.error_state in _ALLOWED_ERROR_STATES else None),
            createdAt=draft.created_at.isoformat() if draft.created_at else "",
            updatedAt=draft.updated_at.isoformat() if draft.updated_at else "",
        )

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

    async def _global_discovery(
        self,
        *,
        kb: KnowledgeBase,
        papers: list[Paper],
        question: str,
        routing: PhaseIRoutingDecision,
    ) -> tuple[dict[str, Any], Optional[str]]:
        # Graph assist is enabled only when KB config turns it on and Neo4j is healthy.
        graph_assist_used = False
        graph_error: Optional[str] = None
        if kb.enable_graph:
            graph_assist_used = await self._is_graph_available()
            if not graph_assist_used:
                graph_error = "graph_unavailable"

        themes = self._derive_themes_from_titles([p.title for p in papers])
        candidate_papers = [p.id for p in papers]
        return {
            "query_family": "survey",
            "graph_assist_used": graph_assist_used,
            "themes": themes,
            "candidate_papers": candidate_papers,
            "section_seeds": [
                {
                    "title": "Research Landscape",
                    "intent": f"Map the literature landscape for: {question}",
                    "perspective": "landscape",
                    "retrieval_mode": routing.execution_mode,
                },
                {
                    "title": "Method Trends",
                    "intent": "Compare methods, assumptions, and design patterns across papers",
                    "perspective": "methods",
                    "retrieval_mode": routing.execution_mode,
                },
                {
                    "title": "Conflicting Evidence",
                    "intent": "Surface disagreement, boundary conditions, and contradictory findings",
                    "perspective": "conflicts",
                    "retrieval_mode": routing.execution_mode,
                },
                {
                    "title": "Limitations and Gaps",
                    "intent": "Summarize weaknesses, missing evidence, and open research gaps",
                    "perspective": "gaps",
                    "retrieval_mode": routing.execution_mode,
                },
            ],
            "storm_lite_used": routing.review_strategy == "storm_lite",
        }, graph_error

    async def _is_graph_available(self) -> bool:
        neo4j = Neo4jService()
        try:
            async with neo4j.driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await neo4j.close()

    @staticmethod
    def _derive_themes_from_titles(titles: list[str]) -> list[str]:
        tokens: dict[str, int] = {}
        for title in titles:
            for token in title.lower().replace(":", " ").replace("-", " ").split():
                clean = token.strip(".,()[]{}")
                if len(clean) < 4:
                    continue
                if clean in {"with", "from", "that", "this", "using", "study", "toward", "towards"}:
                    continue
                tokens[clean] = tokens.get(clean, 0) + 1
        ordered = sorted(tokens.items(), key=lambda kv: kv[1], reverse=True)
        return [word for word, _ in ordered[:6]]

    def _build_outline(
        self,
        *,
        papers: list[Paper],
        question: str,
        graph_summary: dict[str, Any],
        routing: PhaseIRoutingDecision,
    ) -> OutlineDoc:
        seeds = graph_summary.get("section_seeds") or []
        themes = graph_summary.get("themes") or []
        paper_ids = [p.id for p in papers]
        sections = []
        for seed in seeds:
            sections.append(
                OutlineSection(
                    title=seed.get("title", "Section"),
                    intent=seed.get("intent", "Synthesize evidence"),
                    perspective=seed.get("perspective", "synthesis"),
                    retrieval_mode=seed.get("retrieval_mode", routing.execution_mode),
                    supporting_paper_ids=paper_ids,
                    seed_evidence=[],
                )
            )
        return OutlineDoc(
            research_question=question,
            themes=themes,
            sections=sections,
        )

    def _retrieve_section_evidence(
        self,
        *,
        user_id: str,
        paper_ids: list[str],
        outline_doc: OutlineDoc,
        routing: PhaseIRoutingDecision,
        steps: list[dict[str, Any]],
        tool_events: list[dict[str, Any]],
    ) -> list[EvidenceRetrieverOutput]:
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
                pack = self._retrieve_evidence(
                    query=query,
                    user_id=user_id,
                    paper_scope=paper_ids,
                    query_family="survey",
                    stage="rule",
                    top_k=top_k,
                )
                blocks = [self._candidate_to_evidence_block(c) for c in pack.candidates[:top_k]]
                blocks = self._diversify_evidence_blocks(blocks=blocks, limit=top_k)
                if not blocks and paper_ids:
                    blocks = self._retrieve_live_evidence_fallback(
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
            self._step(
                step_name="evidence_retriever",
                input_schema_name="EvidenceRetrieverInput",
                output_schema_name="EvidenceRetrieverOutput",
                status="completed",
            )
        )
        return outputs

    def _retrieve_live_evidence_fallback(
        self,
        *,
        query: str,
        user_id: str,
        paper_ids: list[str],
        top_k: int = 6,
    ) -> list[EvidenceBlock]:
        """Fallback to the live Milvus paper contents collection for fresh imports.

        The review pipeline's primary retriever is artifact-backed and can miss
        newly imported papers that have not been materialized into the static
        artifact index yet. For paper-scoped review generation we can safely
        fall back to the live per-user Milvus collection.
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

    @staticmethod
    def _diversify_evidence_blocks(*, blocks: list[EvidenceBlock], limit: int) -> list[EvidenceBlock]:
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

    @staticmethod
    def _synthesize_section_text(
        *,
        question: str,
        section: OutlineSection,
        evidence_blocks: list[EvidenceBlock],
    ) -> str:
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

    def _write_draft(
        self,
        *,
        outline_doc: OutlineDoc,
        section_evidence: list[EvidenceRetrieverOutput],
        routing: PhaseIRoutingDecision,
    ) -> DraftDoc:
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
            text = self._synthesize_section_text(
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

            paragraph = DraftParagraph(
                paragraph_id=uuid4().hex[:12],
                text=text,
                citations=citation_rows,
                evidence_blocks=top_blocks,
                claim_verification=self._build_claim_verification(text=text, evidence_blocks=top_blocks),
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

    @staticmethod
    def _build_claim_verification(*, text: str, evidence_blocks: list[EvidenceBlock]) -> list[dict[str, Any]]:
        report = get_truthfulness_service().evaluate_text(text=text, evidence_blocks=evidence_blocks)
        return ReviewDraftService._truthfulness_report_to_claim_rows(report)

    @staticmethod
    def _truthfulness_report_to_claim_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in report.get("results", []):
            results.append(
                {
                    "claim_id": item["claim_id"],
                    "claim_text": item["text"],
                    "claim_type": item["claim_type"],
                    "support_status": item["support_level"],
                    "support_score": item["support_score"],
                    "supporting_evidence_ids": item["evidence_ids"],
                    "repairable": item["support_level"] != "supported",
                    "repair_hint": item["reason"],
                }
            )
        return results

    @staticmethod
    def _merge_claim_rows(
        *,
        refreshed_rows: list[dict[str, Any]],
        repaired_claim: dict[str, Any],
    ) -> list[dict[str, Any]]:
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

    @staticmethod
    def _build_truthfulness_summary(
        *,
        claim_rows: list[dict[str, Any]],
        verifier_backend: str,
    ) -> dict[str, Any]:
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

    def _validate_draft(self, draft_doc: DraftDoc) -> tuple[DraftDoc, list[CitationValidatorOutput]]:
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

    def _finalize(
        self,
        *,
        finalizer_input: DraftFinalizerInput,
        graph_used: bool,
        graph_error: Optional[str],
        routing: PhaseIRoutingDecision,
    ) -> tuple[DraftDoc, ReviewQuality, Optional[str]]:
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

        quality = ReviewQuality(
            citation_coverage=citation_coverage,
            unsupported_paragraph_rate=unsupported_rate,
            graph_assist_used=graph_used,
            fallback_used=fallback_used,
            execution_mode=routing.execution_mode,
            kernel_profile=routing.kernel_scope,
            storm_lite_used=routing.review_strategy == "storm_lite",
            adaptive_routing_used=routing.retrieval_plane_policy.get("routing_policy") == "adaptive_depth",
            truthfulness_backend=routing.verification_backend,
            benchmark_hooks={
                "task_family": routing.task_family,
                "execution_mode": routing.execution_mode,
                "truthfulness_report_summary": {
                    "unsupported_claim_rate": round(unsupported_rate, 4),
                    "citation_coverage": round(citation_coverage, 4),
                    "verifier_backend": routing.verification_backend,
                },
                "retrieval_plane_policy": routing.retrieval_plane_policy,
                "degraded_conditions": [graph_error] if graph_error else [],
            },
        )
        return draft_doc, quality, error_state

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
    def _candidate_to_evidence_block(cand: EvidenceCandidate) -> EvidenceBlock:
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

    @staticmethod
    def to_run_summary(run: ReviewRun) -> dict[str, Any]:
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

    @staticmethod
    def to_run_detail(run: ReviewRun) -> dict[str, Any]:
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
