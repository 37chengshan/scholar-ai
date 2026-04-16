"""Pydantic models for RAG API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    text: str = Field(..., min_length=1)
    paper_id: str = Field(...)
    chunk_id: str = Field(...)
    content_preview: Optional[str] = Field(default=None, max_length=500)
    page: Optional[int] = Field(default=None, ge=1)
    similarity: float = Field(..., ge=0.0, le=1.0)
    title: Optional[str] = Field(default=None, max_length=500)

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Citation text cannot be empty")
        return v.strip()


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    paper_ids: List[str] = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    include_citations: bool = Field(default=True)
    max_tokens: Optional[int] = Field(default=1000, ge=100, le=4000)
    stream: bool = Field(default=False)

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class RAGResponse(BaseModel):
    answer: str = Field(...)
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    tokens_used: Optional[int] = Field(default=None, ge=0)
    query_time_ms: Optional[int] = Field(default=None, ge=0)


class RAGStreamChunk(BaseModel):
    type: str = Field(..., pattern=r"^(token|citations|done|error)$")
    content: Optional[str] = Field(default=None)


class RAGQueryResult(BaseModel):
    answer: str
    contexts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
