"""Upload session API endpoints for resumable local-file imports."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.schemas.upload_session import CreateUploadSessionRequest
from app.services.upload_session_service import UploadSessionService
from app.utils.problem_detail import Errors

router = APIRouter()
_service = UploadSessionService()


class UploadSessionResponse(BaseModel):
    success: bool = True
    data: dict[str, Any]


def _raise_value_error(e: ValueError) -> None:
    """Map service validation/not-found errors to consistent HTTP responses."""
    message = str(e)
    if "not found" in message.lower():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=Errors.not_found(message),
        )

    raise HTTPException(
        status_code=http_status.HTTP_400_BAD_REQUEST,
        detail=Errors.validation(message),
    )


@router.post("/import-jobs/{job_id}/upload-sessions", response_model=UploadSessionResponse)
async def create_upload_session(
    job_id: str,
    request: CreateUploadSessionRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Create or resume upload session for a local-file import job."""
    try:
        result = await _service.create_session(job_id, user_id, request, db)
        return UploadSessionResponse(success=True, data=result)
    except ValueError as e:
        _raise_value_error(e)


@router.get("/upload-sessions/{session_id}", response_model=UploadSessionResponse)
async def get_upload_session(
    session_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Get upload session state and missing part list."""
    try:
        session = await _service.get_session(session_id, user_id, db)
        return UploadSessionResponse(success=True, data=_service.serialize_session(session))
    except ValueError as e:
        _raise_value_error(e)


@router.put("/upload-sessions/{session_id}/parts/{part_number}", response_model=UploadSessionResponse)
async def upload_part(
    session_id: str,
    part_number: int,
    request: Request,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload a single chunk for the target upload session."""
    try:
        content = await request.body()
        result = await _service.register_part(session_id, user_id, part_number, content, db)
        return UploadSessionResponse(success=True, data=result)
    except ValueError as e:
        _raise_value_error(e)


@router.post("/upload-sessions/{session_id}/complete", response_model=UploadSessionResponse)
async def complete_upload_session(
    session_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Complete upload session, assemble file and enqueue import worker."""
    try:
        result = await _service.complete_session(session_id, user_id, db)
        return UploadSessionResponse(success=True, data=result)
    except ValueError as e:
        _raise_value_error(e)


@router.post("/upload-sessions/{session_id}/abort", response_model=UploadSessionResponse)
async def abort_upload_session(
    session_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Abort upload session and prevent further writes."""
    try:
        result = await _service.abort_session(session_id, user_id, db)
        return UploadSessionResponse(success=True, data=result)
    except ValueError as e:
        _raise_value_error(e)


__all__ = ["router"]
