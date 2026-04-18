"""Pydantic schemas for upload session API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateUploadSessionRequest(BaseModel):
    filename: str
    size_bytes: int = Field(gt=0, alias="sizeBytes")
    chunk_size: int = Field(default=5 * 1024 * 1024, gt=0, le=20 * 1024 * 1024, alias="chunkSize")
    sha256: Optional[str] = None
    mime_type: Optional[str] = Field(default="application/pdf", alias="mimeType")

    class Config:
        populate_by_name = True


class UploadSessionStateDto(BaseModel):
    upload_session_id: str = Field(alias="uploadSessionId")
    import_job_id: str = Field(alias="importJobId")
    status: str
    chunk_size: int = Field(alias="chunkSize")
    total_parts: int = Field(alias="totalParts")
    uploaded_parts: list[int] = Field(alias="uploadedParts")
    missing_parts: list[int] = Field(alias="missingParts")
    uploaded_bytes: int = Field(alias="uploadedBytes")
    size_bytes: int = Field(alias="sizeBytes")
    progress: int
    expires_at: datetime = Field(alias="expiresAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")

    class Config:
        populate_by_name = True
