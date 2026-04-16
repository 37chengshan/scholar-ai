"""Pydantic models for Note management."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    paper_ids: List[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[List[str]] = Field(default=None)
    paper_ids: Optional[List[str]] = Field(default=None)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(...)
    user_id: str = Field(...)
    title: str = Field(...)
    content: str = Field(...)
    tags: List[str] = Field(default_factory=list)
    paper_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class NoteListResponse(BaseModel):
    notes: List[NoteResponse] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
