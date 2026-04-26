from __future__ import annotations

from typing import Literal

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
    diagnostics: dict[str, float] = Field(default_factory=dict)


class AnswerClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    support_status: Literal["supported", "partially_supported", "unsupported"]
    supporting_source_chunk_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class AnswerContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_mode: Literal["full", "partial", "abstain"]
    claims: list[AnswerClaim] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
