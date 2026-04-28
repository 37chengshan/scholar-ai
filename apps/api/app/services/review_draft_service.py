"""Phase 5 ReviewDraft service.

Implements a practical global-local review pipeline:
- outline_planner
- evidence_retriever
- review_writer
- citation_validator
- draft_finalizer
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j_service import Neo4jService
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
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
            )
            artifacts.append({"type": "outline", "section_count": len(outline_doc.sections)})

            section_evidence = self._retrieve_section_evidence(
                user_id=user_id,
                paper_ids=source_paper_ids,
                outline_doc=outline_doc,
                steps=steps,
                tool_events=tool_events,
            )

            draft_doc = self._write_draft(outline_doc=outline_doc, section_evidence=section_evidence)
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
                {"title": "Research Landscape", "intent": f"Survey: {question}"},
                {"title": "Method Trends", "intent": "Compare methods and assumptions"},
                {"title": "Limitations and Gaps", "intent": "Summarize weaknesses and open problems"},
            ],
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
                    },
                    "status": "running",
                }
            )

            query = f"{section.title}. {section.intent}"
            pack = self._retrieve_evidence(
                query=query,
                user_id=user_id,
                paper_scope=paper_ids,
                query_family="survey",
                stage="rule",
                top_k=6,
            )
            blocks = [self._candidate_to_evidence_block(c) for c in pack.candidates[:6]]
            outputs.append(
                EvidenceRetrieverOutput(
                    section_title=section.title,
                    evidence_bundles=blocks,
                )
            )

            tool_events.append(
                {
                    "event_id": tool_event_id,
                    "tool_name": "hybrid_retriever",
                    "event_type": "result",
                    "result": {
                        "candidate_count": len(pack.candidates),
                        "paper_coverage_count": int(pack.diagnostics.get("paper_coverage_count", 0.0)),
                    },
                    "status": "success",
                }
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

    def _write_draft(self, *, outline_doc: OutlineDoc, section_evidence: list[EvidenceRetrieverOutput]) -> DraftDoc:
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

            top_blocks = section_bundle.evidence_bundles[:2]
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
            text = " ".join([b.text for b in top_blocks if b.text]).strip()
            if not text:
                text = "Evidence found but no extractable text snippet."

            paragraph = DraftParagraph(
                paragraph_id=uuid4().hex[:12],
                text=text,
                citations=citation_rows,
                evidence_blocks=top_blocks,
                citation_coverage_status="covered",
            )
            sections.append(
                DraftSection(
                    heading=section.title,
                    paragraphs=[paragraph],
                )
            )
        return DraftDoc(sections=sections)

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
                "supported" if cand.rerank_score >= 0.7 else "partially_supported" if cand.rerank_score >= 0.4 else "unsupported"
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
