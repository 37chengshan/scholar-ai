"""Shared models and helpers for papers module.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.models import Paper, ProcessingTask, PaperChunk, ReadingProgress
from app.utils.problem_detail import ProblemDetail, ErrorTypes
from app.utils.logger import logger


# =============================================================================
# Request/Response Models
# =============================================================================


class PaperListResponse(BaseModel):
    """Paper list response with pagination."""

    success: bool = True
    data: dict


class PaperCreateRequest(BaseModel):
    """Request to create a new paper (get upload URL)."""

    filename: str


class PaperCreateResponse(BaseModel):
    """Response for paper creation."""

    success: bool = True
    data: dict


class PaperResponse(BaseModel):
    """Single paper response with full details."""

    success: bool = True
    data: "PaperData"
    meta: Optional[dict] = None


class PaperData(BaseModel):
    """Full paper data structure."""

    id: str
    title: str
    authors: list[str]
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    content: Optional[str] = None
    imrad_json: Optional[dict] = None
    status: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    keywords: Optional[list[str]] = None
    venue: Optional[str] = None
    citations: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_id: str
    storage_key: Optional[str] = None
    reading_notes: Optional[str] = None
    reading_card_doc: Optional[dict] = None
    notes_version: Optional[int] = None
    starred: bool = False
    project_id: Optional[str] = None
    batch_id: Optional[str] = None
    upload_progress: Optional[int] = None
    upload_status: Optional[str] = None
    uploaded_at: Optional[str] = None
    processingStatus: Optional[str] = None
    progress: int = 0
    processingError: Optional[str] = None
    chunks: Optional[list["ChunkData"]] = None


class ChunkData(BaseModel):
    """Paper chunk data structure."""

    id: str
    content: str
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    is_table: bool = False
    is_figure: bool = False


class BatchDeleteResponse(BaseModel):
    """Batch delete operation response."""

    success: bool = True
    data: "BatchDeleteData"


class BatchDeleteData(BaseModel):
    """Batch delete result data."""

    deletedCount: int = Field(description="Number of papers successfully deleted")
    requestedCount: int = Field(description="Total number of papers requested for deletion")
    failedIds: list[str] = Field(
        default_factory=list,
        description="IDs of papers that failed to delete"
    )
    message: str


class BatchStarResponse(BaseModel):
    """Batch star/unstar operation response."""

    success: bool = True
    data: "BatchStarData"


class BatchStarData(BaseModel):
    """Batch star result data."""

    updatedCount: int = Field(description="Number of papers successfully updated")
    requestedCount: int = Field(description="Total number of papers requested")
    failedIds: list[str] = Field(
        default_factory=list,
        description="IDs of papers that failed to update"
    )
    starred: bool = Field(description="Starred status applied")
    message: str


class MessageResponse(BaseModel):
    """Simple message response."""

    success: bool = True
    data: "MessageData"


class MessageData(BaseModel):
    """Message data structure."""

    message: str


class PaperUpdateRequest(BaseModel):
    """Request to update paper metadata."""

    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    starred: Optional[bool] = None
    projectId: Optional[str] = None


class StarredRequest(BaseModel):
    """Request to toggle starred status."""

    starred: bool


class WebhookRequest(BaseModel):
    """Upload completion webhook request."""

    paperId: str
    storageKey: str


# =============================================================================
# Helper Functions
# =============================================================================


def create_error_response(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    instance: str,
) -> HTTPException:
    """Create HTTPException with RFC 7807 ProblemDetail."""
    problem = ProblemDetail(
        type=error_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
    )
    return HTTPException(
        status_code=status_code,
        detail=problem.to_dict(),
    )


def get_progress_percent(processing_status: str) -> int:
    """Calculate progress percentage based on processing status."""
    progress_map = {
        "pending": 0,
        "processing_ocr": 15,
        "parsing": 30,
        "extracting_imrad": 45,
        "generating_notes": 60,
        "storing_vectors": 75,
        "indexing_multimodal": 90,
        "completed": 100,
        "failed": 0,
    }
    return progress_map.get(processing_status, 0)


def get_processing_stage(status: str) -> str:
    """Get human-readable processing stage name."""
    stage_names = {
        "processing_ocr": "OCR Processing",
        "parsing": "Parsing Document",
        "extracting_imrad": "Extracting Structure",
        "generating_notes": "Generating Notes",
        "storing_vectors": "Storing Vectors",
        "indexing_multimodal": "Indexing Multimodal",
        "completed": "Completed",
        "failed": "Failed",
        "pending": "Pending",
    }
    return stage_names.get(status, status)


def format_paper_response(paper: Paper, task: Optional[ProcessingTask] = None) -> dict:
    """Format paper for API response."""
    paper_dict = {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "pdf_url": paper.pdf_url,
        "pdf_path": paper.pdf_path,
        "content": paper.content,
        "imrad_json": paper.imrad_json,
        "status": paper.status,
        "file_size": paper.file_size,
        "page_count": paper.page_count,
        "keywords": paper.keywords,
        "venue": paper.venue,
        "citations": paper.citations,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        "user_id": paper.user_id,
        "storage_key": paper.storage_key,
        "reading_notes": paper.reading_notes,
        "reading_card_doc": paper.reading_card_doc,
        "notes_version": paper.notes_version,
        "starred": paper.starred,
        "project_id": paper.project_id,
        "batch_id": paper.batch_id,
        "upload_progress": paper.upload_progress,
        "upload_status": paper.upload_status,
        "uploaded_at": paper.uploaded_at.isoformat() if paper.uploaded_at else None,
    }

    processing_status = task.status if task else paper.status or "pending"
    paper_dict["processingStatus"] = processing_status
    paper_dict["progress"] = get_progress_percent(processing_status)
    paper_dict["processingError"] = task.error_message if task else None

    return paper_dict


__all__ = [
    "PaperListResponse",
    "PaperCreateRequest",
    "PaperCreateResponse",
    "PaperResponse",
    "PaperData",
    "ChunkData",
    "BatchDeleteResponse",
    "BatchDeleteData",
    "BatchStarResponse",
    "BatchStarData",
    "MessageResponse",
    "MessageData",
    "PaperUpdateRequest",
    "StarredRequest",
    "WebhookRequest",
    "create_error_response",
    "get_progress_percent",
    "get_processing_stage",
    "format_paper_response",
    "datetime",
    "timezone",
    "uuid4",
    "status",
    "func",
    "logger",
]
