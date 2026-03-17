"""Pydantic models for RAG (Retrieval-Augmented Generation) API.

Defines request/response schemas for:
- RAG query requests with paper filtering
- RAG responses with citations
- Citation metadata for answer provenance
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    """Citation metadata for RAG answer provenance.

    Tracks the source of information used to generate an answer,
    including paper reference, page number, and relevance score.
    """

    text: str = Field(
        ...,
        description="The cited text from the paper chunk",
        min_length=1,
    )
    paper_id: str = Field(
        ...,
        description="UUID of the source paper",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )
    chunk_id: str = Field(
        ...,
        description="UUID of the specific chunk",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )
    content_preview: Optional[str] = Field(
        default=None,
        description="Preview of the chunk content for display",
        max_length=500,
    )
    page: Optional[int] = Field(
        default=None,
        description="Page number where the citation appears",
        ge=1,
    )
    similarity: float = Field(
        ...,
        description="Similarity score between query and chunk (0-1)",
        ge=0.0,
        le=1.0,
    )
    title: Optional[str] = Field(
        default=None,
        description="Title of the source paper",
        max_length=500,
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Citation text cannot be empty")
        return v.strip()


class RAGQueryRequest(BaseModel):
    """RAG query request with paper filtering.

    Supports single-paper and cross-paper queries with
    configurable retrieval parameters.
    """

    question: str = Field(
        ...,
        description="The question to answer based on paper content",
        min_length=1,
        max_length=2000,
    )
    paper_ids: List[str] = Field(
        ...,
        description="List of paper UUIDs to search within",
        min_length=1,
    )
    top_k: int = Field(
        default=5,
        description="Number of chunks to retrieve for context",
        ge=1,
        le=20,
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to include full citation metadata",
    )
    max_tokens: Optional[int] = Field(
        default=1000,
        description="Maximum tokens for generated answer",
        ge=100,
        le=4000,
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response",
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        """Ensure question is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

    @field_validator("paper_ids")
    @classmethod
    def validate_paper_ids(cls, v: List[str]) -> List[str]:
        """Validate that paper_ids are valid UUIDs."""
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )
        for paper_id in v:
            if not uuid_pattern.match(paper_id):
                raise ValueError(f"Invalid paper_id format: {paper_id}")
        return v


class RAGResponse(BaseModel):
    """RAG query response with answer and citations.

    Provides the generated answer along with source citations
    for transparency and verification.
    """

    answer: str = Field(
        ...,
        description="Generated answer to the question",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations supporting the answer",
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the answer (0-1)",
        ge=0.0,
        le=1.0,
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description="Number of tokens used in generation",
        ge=0,
    )
    query_time_ms: Optional[int] = Field(
        default=None,
        description="Query execution time in milliseconds",
        ge=0,
    )


class RAGStreamChunk(BaseModel):
    """Single chunk in a streaming RAG response.

    Used for SSE (Server-Sent Events) streaming format.
    """

    type: str = Field(
        ...,
        description="Event type: token, citations, or done",
        pattern=r"^(token|citations|done|error)$",
    )
    content: Optional[str] = Field(
        default=None,
        description="Token content or JSON-serialized data",
    )


class RAGQueryResult(BaseModel):
    """Internal result from RAG service before formatting.

    Represents the raw result from PaperQA2 or similar engine.
    """

    answer: str
    contexts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
