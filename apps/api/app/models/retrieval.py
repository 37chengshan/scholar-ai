"""Pydantic models for unified retrieval schema.

Defines data contracts for the RAG pipeline:
- RetrievedChunk: Unified chunk representation from Milvus search
- CitationSource: Source reference for synthesis output
- SearchConstraints: Filter constraints for metadata-aware search

Field mapping from raw vector hits:
- text payload -> text
- normalized relevance -> score
- canonical page index -> page_num

Per Phase 40 D-01 specification.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RetrievedChunk(BaseModel):
    """Unified chunk representation from Milvus search.

    Standard field names for RAG synthesis layer:
    - text: Chunk content
    - score: Relevance score (0.0-1.0)
    - page_num: Page number in paper

    This keeps downstream synthesis code on a single canonical retrieval schema.
    """

    model_config = ConfigDict(from_attributes=True)

    paper_id: str = Field(
        ...,
        description="Paper UUID",
    )
    paper_title: Optional[str] = Field(
        default=None,
        description="Paper title (optional, for citation display)",
        max_length=500,
    )
    text: str = Field(
        ...,
        description="Chunk content text",
    )
    text_span: Optional[str] = Field(
        default=None,
        description="Evidence span text for bundle-level retrieval",
    )
    score: float = Field(
        ...,
        description="Relevance score (0.0-1.0, unified field)",
        ge=0.0,
        le=1.0,
    )
    backend: str = Field(
        default="milvus",
        description="Vector backend that produced this chunk",
        pattern=r"^(milvus|qdrant)$",
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Stable source/chunk identifier",
    )
    page_num: Optional[int] = Field(
        default=None,
        description="Page number in paper",
        ge=1,
    )
    section_path: Optional[str] = Field(
        default=None,
        description="Canonical section path for retrieval contract",
        max_length=200,
    )
    content_subtype: Optional[str] = Field(
        default=None,
        description="Canonical content subtype (paragraph/figure/table_caption/etc.)",
        max_length=100,
    )
    anchor_text: Optional[str] = Field(
        default=None,
        description="Anchor snippet used for claim-level citation alignment",
        max_length=300,
    )
    section: Optional[str] = Field(
        default=None,
        description="IMRaD section (Introduction, Methods, Results, Discussion)",
        max_length=100,
    )
    paper_role: Optional[str] = Field(
        default=None,
        description="Academic paper role for this chunk",
        pattern=r"^(method|result|limitation|ablation|conclusion)$",
    )
    table_ref: Optional[str] = Field(
        default=None,
        description="Referenced table identifier",
        max_length=120,
    )
    figure_ref: Optional[str] = Field(
        default=None,
        description="Referenced figure identifier",
        max_length=120,
    )
    metric_sentence: Optional[str] = Field(
        default=None,
        description="Sentence containing metric evidence",
        max_length=1000,
    )
    dataset: Optional[str] = Field(
        default=None,
        description="Dataset name extracted for evidence bundle",
        max_length=200,
    )
    baseline: Optional[str] = Field(
        default=None,
        description="Baseline method name",
        max_length=200,
    )
    method: Optional[str] = Field(
        default=None,
        description="Method name extracted from chunk",
        max_length=200,
    )
    score_value: Optional[float] = Field(
        default=None,
        description="Numeric metric value in evidence",
    )
    metric_name: Optional[str] = Field(
        default=None,
        description="Metric name (accuracy/f1/etc.)",
        max_length=120,
    )
    metric_direction: Optional[str] = Field(
        default=None,
        description="Metric optimization direction",
        pattern=r"^(higher_better|lower_better|neutral)$",
    )
    caption_text: Optional[str] = Field(
        default=None,
        description="Figure or table caption text",
        max_length=1000,
    )
    evidence_bundle_id: Optional[str] = Field(
        default=None,
        description="Stable identifier for grouped evidence bundle",
        max_length=200,
    )
    evidence_types: List[str] = Field(
        default_factory=list,
        description="Evidence types included in this bundle (text/table/image/caption)",
    )
    content_type: str = Field(
        default="text",
        description="Content type: text, image, table",
        pattern=r"^(text|image|table)$",
    )
    quality_score: Optional[float] = Field(
        default=None,
        description="Quality score (0.0-1.0) from chunk quality algorithm",
        ge=0.0,
        le=1.0,
    )
    raw_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw data for multimodal content (image/table metadata)",
    )
    vector_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sparse_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hybrid_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reranker_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    retrieval_trace_id: Optional[str] = Field(
        default=None,
        description="Trace identifier for retrieval debugging",
    )
    milvus_collection: Optional[str] = Field(
        default=None,
        description="Milvus collection used by live search",
        max_length=200,
    )
    milvus_stage: Optional[str] = Field(
        default=None,
        description="Collection stage inferred from live retrieval (raw/rule/llm)",
        max_length=20,
    )
    milvus_search_path: Optional[str] = Field(
        default=None,
        description="Live search path (primary/minimal_retry/query_fallback)",
        max_length=64,
    )
    milvus_output_fields: List[str] = Field(
        default_factory=list,
        description="output_fields used in Milvus search",
    )
    milvus_fallback_used: bool = Field(
        default=False,
        description="Whether Milvus retrieval fell back to query-based cosine path",
    )
    milvus_unsupported_field_type_count: int = Field(
        default=0,
        description="Unsupported field type errors seen in this retrieval path",
        ge=0,
    )
    # Iteration 2: multi-index fields
    index_type: Optional[str] = Field(
        default=None,
        description="Index tier that produced this chunk (local_evidence/structural/summary)",
        max_length=40,
    )
    context_window: Optional[str] = Field(
        default=None,
        description="Expanded neighbouring context included in contextual chunk",
        max_length=600,
    )
    subsection: Optional[str] = Field(
        default=None,
        description="Leaf subsection label within the section path",
        max_length=120,
    )


class CitationSource(BaseModel):
    """Source reference for synthesis output.

    Used in answer citations to reference specific chunks:
    - text_preview: Truncated content for citation display
    - score: Relevance score for ranking sources
    """

    model_config = ConfigDict(from_attributes=True)

    paper_id: str = Field(
        ...,
        description="Paper UUID",
    )
    paper_title: Optional[str] = Field(
        default=None,
        description="Paper title for citation display",
        max_length=500,
    )
    section: Optional[str] = Field(
        default=None,
        description="IMRaD section for citation",
        max_length=100,
    )
    page_num: Optional[int] = Field(
        default=None,
        description="Page number for citation",
        ge=1,
    )
    content_type: str = Field(
        default="text",
        description="Content type: text, image, table",
    )
    text_preview: str = Field(
        ...,
        description="Truncated text preview (max 300 chars)",
        max_length=300,
    )
    score: float = Field(
        ...,
        description="Relevance score for ranking",
        ge=0.0,
        le=1.0,
    )


class SearchConstraints(BaseModel):
    """Filter constraints for metadata-aware search.

    Used to build Milvus expr filters from user query metadata:
    - paper_ids: Restrict search to specific papers
    - year_from/year_to: Temporal filtering
    - section: IMRaD section filtering
    - content_types: Modality filtering
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(
        ...,
        description="User UUID for ownership filtering",
    )
    paper_ids: List[str] = Field(
        default_factory=list,
        description="List of paper UUIDs to search within",
    )
    year_from: Optional[int] = Field(
        default=None,
        description="Minimum publication year",
        ge=1900,
        le=2100,
    )
    year_to: Optional[int] = Field(
        default=None,
        description="Maximum publication year",
        ge=1900,
        le=2100,
    )
    section: Optional[str] = Field(
        default=None,
        description="IMRaD section filter",
        max_length=100,
    )
    content_types: List[str] = Field(
        default_factory=list,
        description="Content type filters: text, image, table",
    )
    min_quality_score: Optional[float] = Field(
        default=None,
        description="Minimum quality score threshold",
        ge=0.0,
        le=1.0,
    )
    index_type: Optional[str] = Field(
        default=None,
        description="Index tier to search (local_evidence/structural/summary)",
        max_length=40,
    )