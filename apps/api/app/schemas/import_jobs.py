"""Import job DTO schemas for shared contract convergence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ImportJobStatus = Literal[
    "created",
    "queued",
    "running",
    "awaiting_user_action",
    "completed",
    "failed",
    "cancelled",
]


class ImportJobDto(BaseModel):
    import_job_id: str
    knowledge_base_id: str
    source_type: str
    status: ImportJobStatus
    stage: str
    progress: int = Field(default=0, ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class UploadHistoryRecordDto(BaseModel):
    id: str
    user_id: str
    paper_id: Optional[str] = None
    filename: str
    status: str
    chunks_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
