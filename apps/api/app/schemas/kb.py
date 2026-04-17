"""Knowledge base DTO schemas for shared contract convergence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeBaseDto(BaseModel):
    id: str
    user_id: str
    name: str
    description: str = ""
    category: str = "other"
    paper_count: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)
    embedding_model: str
    parse_engine: str
    chunk_strategy: str
    enable_graph: bool = False
    enable_imrad: bool = False
    enable_chart_understanding: bool = False
    enable_multimodal_search: bool = False
    enable_comparison: bool = False
    created_at: datetime
    updated_at: datetime


class KnowledgeBasePaperDto(BaseModel):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    status: str
    chunk_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)


class KnowledgeBaseSearchHitDto(BaseModel):
    id: str
    paper_id: str
    paper_title: Optional[str] = None
    content: str
    section: Optional[str] = None
    page: Optional[int] = None
    score: float
