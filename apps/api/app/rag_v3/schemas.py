from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


QueryFamily = Literal[
    "fact",
    "method",
    "table",
    "figure",
    "numeric",
    "compare",
    "cross_paper",
    "survey",
    "related_work",
    "method_evolution",
    "conflicting_evidence",
    "hard",
]


class PaperSummaryArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    parse_id: str
    title: str = ""
    abstract: str = ""
    paper_summary: str = ""
    method_summary: str = ""
    experiment_summary: str = ""
    result_summary: str = ""
    limitation_summary: str = ""
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    table_captions: list[str] = Field(default_factory=list)
    figure_captions: list[str] = Field(default_factory=list)
    representative_source_chunk_ids: list[str] = Field(default_factory=list)
    created_at: str


class SectionSummaryArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    paper_id: str
    parse_id: str
    section_path: str
    normalized_section_path: str
    section_title: str
    section_summary: str
    key_terms: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    figure_ids: list[str] = Field(default_factory=list)
    created_at: str


class RelationNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["paper", "method", "dataset", "metric", "claim", "result", "task", "limitation", "baseline", "figure", "table", "citation"]
    id: str
    text: str


class RelationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation_id: str
    subject: RelationNode
    predicate: Literal[
        "uses_method",
        "evaluates_on",
        "reports_metric",
        "outperforms",
        "underperforms",
        "compares_with",
        "extends",
        "contradicts",
        "shares_dataset",
        "has_limitation",
        "cites",
    ]
    object: RelationNode
    paper_id: str
    evidence_source_chunk_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: str


class EvidenceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_chunk_id: str
    paper_id: str
    section_id: str = ""
    content_type: Literal["text", "table", "figure", "caption", "page"] = "text"
    anchor_text: str = ""
    candidate_sources: list[str] = Field(default_factory=list)
    dense_score: float = 0.0
    lexical_score: float = 0.0
    numeric_score: float = 0.0
    caption_score: float = 0.0
    graph_score: float = 0.0
    rrf_score: float = 0.0
    pre_rerank_rank: int = 0
    post_rerank_rank: int = 0
    rerank_score: float = 0.0


class EvidenceQualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    answerability: Literal["full", "partial", "abstain"]
    paper_coverage_score: float = Field(ge=0.0, le=1.0)
    section_match_score: float = Field(ge=0.0, le=1.0)
    content_type_match_score: float = Field(ge=0.0, le=1.0)
    evidence_relevance_score: float = Field(ge=0.0, le=1.0)
    citation_support_score: float = Field(ge=0.0, le=1.0)
    missing_evidence_types: list[str] = Field(default_factory=list)
    recommended_action: Literal["answer", "retry_dense", "retry_sparse", "retry_graph", "retry_caption", "abstain"]


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    query_family: QueryFamily
    stage: str
    candidates: list[EvidenceCandidate] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class AnswerClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    claim_id: str = ""
    claim_type: str = "factual"
    support_status: Literal["supported", "weakly_supported", "partially_supported", "unsupported"]
    support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    repairable: bool = True
    repair_hint: Optional[str] = None
    supporting_source_chunk_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    source_chunk_id: str
    page_num: Optional[int] = None
    section_path: Optional[str] = None
    title: str = ""
    anchor_text: str = ""
    quote_text: str = ""
    source_offset_start: Optional[int] = None
    source_offset_end: Optional[int] = None
    text_preview: str = ""
    score: Optional[float] = None
    content_type: str = "text"
    citation_jump_url: str = ""


class EvidenceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source_type: Literal["paper", "note", "web", "user_upload"] = "paper"
    paper_id: str
    source_chunk_id: str
    page_num: Optional[int] = None
    section_path: Optional[str] = None
    content_type: str = "text"
    text: str = ""
    quote_text: str = ""
    source_offset_start: Optional[int] = None
    source_offset_end: Optional[int] = None
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    support_status: Optional[
        Literal["supported", "weakly_supported", "partially_supported", "unsupported"]
    ] = None
    citation_jump_url: str = ""
    user_comment: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 4: Compare Matrix schemas
# ---------------------------------------------------------------------------


class CompareDimension(BaseModel):
    """A single compare dimension descriptor."""
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class CompareCell(BaseModel):
    """Evidence-backed cell in a compare matrix (paper × dimension)."""
    model_config = ConfigDict(extra="forbid")

    dimension_id: str
    content: str
    support_status: Literal["supported", "partially_supported", "unsupported", "not_enough_evidence"] = "not_enough_evidence"
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)


class CompareRow(BaseModel):
    """One paper's row in the compare matrix."""
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    year: Optional[int] = None
    cells: list[CompareCell] = Field(default_factory=list)


class CrossPaperInsight(BaseModel):
    """A cross-paper insight backed by evidence from multiple papers."""
    model_config = ConfigDict(extra="forbid")

    claim: str
    supporting_paper_ids: list[str] = Field(default_factory=list)
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)


class CompareMatrix(BaseModel):
    """Full multi-paper compare matrix – the canonical Phase 4 output structure."""
    model_config = ConfigDict(extra="forbid")

    paper_ids: list[str]
    dimensions: list[CompareDimension]
    rows: list[CompareRow]
    summary: str = ""
    cross_paper_insights: list[CrossPaperInsight] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Answer Contract
# ---------------------------------------------------------------------------


class AnswerContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["general", "rag", "compare", "review", "reading", "abstain", "error"] = "rag"
    answer_mode: Literal["full", "partial", "abstain"]
    answer: str = ""
    claims: list[AnswerClaim] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    citations: list[AnswerCitation] = Field(default_factory=list)
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    trace_id: str = ""
    run_id: str = ""
    compare_matrix: Optional[CompareMatrix] = None
    task_family: str = ""
    execution_mode: str = ""
    truthfulness_required: bool = False
    truthfulness_summary: dict[str, Any] = Field(default_factory=dict)
    truthfulness_report: dict[str, Any] = Field(default_factory=dict)
    retrieval_plane_policy: dict[str, Any] = Field(default_factory=dict)
    degraded_conditions: list[str] = Field(default_factory=list)
