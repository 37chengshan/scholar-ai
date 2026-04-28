"""Pydantic schemas for Phase 5 ReviewDraft pipeline and API contracts."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.rag_v3.schemas import EvidenceBlock


ReviewDraftStatus = Literal["idle", "running", "completed", "failed", "partial"]
CoverageStatus = Literal["covered", "insufficient"]
ReviewErrorState = Literal[
    "insufficient_evidence",
    "graph_unavailable",
    "validation_failed",
    "writer_failed",
    "partial_draft",
]


class OutlineSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    intent: str
    supporting_paper_ids: list[str] = Field(default_factory=list)
    seed_evidence: list[EvidenceBlock] = Field(default_factory=list)


class OutlineDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_question: str
    themes: list[str] = Field(default_factory=list)
    sections: list[OutlineSection] = Field(default_factory=list)


class DraftParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str
    text: str
    citations: list[dict] = Field(default_factory=list)
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)
    citation_coverage_status: CoverageStatus


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    paragraphs: list[DraftParagraph] = Field(default_factory=list)
    omitted_reason: Optional[str] = None


class DraftDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[DraftSection] = Field(default_factory=list)


class ReviewQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_coverage: float = 0.0
    unsupported_paragraph_rate: float = 0.0
    graph_assist_used: bool = False
    fallback_used: bool = False


class ReviewDraftDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    knowledgeBaseId: str
    title: str
    status: ReviewDraftStatus
    sourcePaperIds: list[str] = Field(default_factory=list)
    outlineDoc: OutlineDoc
    draftDoc: DraftDoc
    quality: ReviewQuality
    traceId: str = ""
    runId: str = ""
    errorState: Optional[ReviewErrorState] = None
    createdAt: str
    updatedAt: str


class ReviewDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_ids: Optional[list[str]] = None
    mode: Literal["outline_and_draft"]
    question: Optional[str] = None
    target_review_draft_id: Optional[str] = None


class ReviewDraftRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Reserve for future controls while keeping endpoint extensible.
    force: bool = False


class ReviewDraftListResponse(BaseModel):
    success: bool = True
    data: dict
    meta: dict


class OutlinePlannerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kb_id: str
    paper_ids: list[str]
    question: str
    graph_summary: dict = Field(default_factory=dict)
    section_candidates: list[dict] = Field(default_factory=list)


class OutlinePlannerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outline_doc: OutlineDoc


class EvidenceRetrieverInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_intent: str
    theme: str
    candidate_papers: list[str]
    local_filters: dict = Field(default_factory=dict)


class EvidenceRetrieverOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_title: str
    evidence_bundles: list[EvidenceBlock] = Field(default_factory=list)


class ReviewWriterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outline_doc: OutlineDoc
    section_evidence_bundles: list[EvidenceRetrieverOutput] = Field(default_factory=list)


class ReviewWriterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_doc: DraftDoc


class CitationValidatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_text: str
    citations: list[dict]
    evidence_blocks: list[EvidenceBlock]


class CitationValidatorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage_status: CoverageStatus
    issues: list[str] = Field(default_factory=list)


class DraftFinalizerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_doc: DraftDoc
    coverage_report: list[CitationValidatorOutput] = Field(default_factory=list)
    run_metadata: dict = Field(default_factory=dict)


class DraftFinalizerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_draft: ReviewDraftDto
