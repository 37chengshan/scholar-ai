"""Paper API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaperListQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    starred: Optional[bool] = None
    read_status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PaperListItem(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxivId: Optional[str] = None
    status: str
    processingStatus: Optional[str] = None
    progress: int = 0
    storageKey: Optional[str] = None
    fileSize: Optional[int] = None
    pageCount: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)
    venue: Optional[str] = None
    citations: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    userId: Optional[str] = None
    readingNotes: Optional[str] = None
    processingError: Optional[str] = None
    starred: bool = False


class PaperListResponse(BaseModel):
    success: bool = True
    data: dict
    meta: dict
