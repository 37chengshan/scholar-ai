"""Pydantic models for unified retrieval schema.

Defines data contracts for the RAG pipeline:
- RetrievedChunk: Unified chunk representation from Milvus search
- CitationSource: Source reference for synthesis output
- SearchConstraints: Filter constraints for metadata-aware search

Field mapping from Milvus Raw Hit:
- content_data -> text (unified field name)
- score -> score (kept as-is, computed from 1-distance)
- page_num -> page_num (unified, not 'page')

Per Phase 40 D-01 specification.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RetrievedChunk(BaseModel):
    """Unified chunk representation from Milvus search.

    Standard field names for RAG synthesis layer:
    - text: Chunk content (mapped from content_data)
    - score: Relevance score (0.0-1.0)
    - page_num: Page number in paper

    This replaces the legacy field names (content, similarity, page) that
    caused field mismatch between Milvus output and synthesis code.
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
        description="Chunk content text (unified field from content_data)",
    )
    score: float = Field(
        ...,
        description="Relevance score (0.0-1.0, unified field)",
        ge=0.0,
        le=1.0,
    )
    page_num: Optional[int] = Field(
        default=None,
        description="Page number in paper (unified field, not 'page')",
        ge=1,
    )
    section: Optional[str] = Field(
        default=None,
        description="IMRaD section (Introduction, Methods, Results, Discussion)",
        max_length=100,
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