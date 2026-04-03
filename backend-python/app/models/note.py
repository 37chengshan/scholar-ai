"""Pydantic models for Note management.

Defines request/response schemas for:
- Note creation with title, content, and paper references
- Note updates with partial field updates
- Note responses with complete note state
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NoteBase(BaseModel):
    """Base fields for Note model."""

    title: str = Field(
        ...,
        description="Note title",
        min_length=1,
        max_length=255,
    )
    content: str = Field(
        ...,
        description="Note content (Markdown format)",
        min_length=1,
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    paper_ids: List[str] = Field(
        default_factory=list,
        description="UUIDs of referenced papers",
    )


class NoteCreate(NoteBase):
    """Schema for creating a new note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating an existing note (partial updates)."""

    title: Optional[str] = Field(
        default=None,
        description="Updated note title",
        min_length=1,
        max_length=255,
    )
    content: Optional[str] = Field(
        default=None,
        description="Updated note content",
        min_length=1,
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated tags list",
    )
    paper_ids: Optional[List[str]] = Field(
        default=None,
        description="Updated paper references",
    )


class NoteResponse(BaseModel):
    """Complete note data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        ...,
        description="Note UUID",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )
    user_id: str = Field(
        ...,
        description="Owner user UUID",
    )
    title: str = Field(
        ...,
        description="Note title",
    )
    content: str = Field(
        ...,
        description="Note content",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags",
    )
    paper_ids: List[str] = Field(
        default_factory=list,
        description="Referenced paper UUIDs",
    )
    created_at: datetime = Field(
        ...,
        description="Note creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )


class NoteListResponse(BaseModel):
    """Paginated list of notes."""

    notes: List[NoteResponse] = Field(
        default_factory=list,
        description="List of notes",
    )
    total: int = Field(
        default=0,
        description="Total number of notes",
        ge=0,
    )
    limit: int = Field(
        default=20,
        description="Number of notes per page",
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0,
    )