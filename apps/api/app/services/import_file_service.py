"""Shared file upload helpers for ImportJob-first flows."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge_base import KnowledgeBase
from app.services.import_job_service import ImportJobService
from app.utils.logger import logger


MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024
DEFAULT_LEGACY_KB_NAME = "Imported Papers"
DEFAULT_LEGACY_KB_DESCRIPTION = "System-created knowledge base for legacy uploads."


def local_storage_root() -> Path:
    """Return the canonical local storage root for uploaded files."""
    return Path(settings.LOCAL_STORAGE_PATH).resolve()


def build_upload_storage_key(user_id: str, import_job_id: str) -> str:
    """Build the canonical storage key for uploaded PDFs."""
    now = datetime.now(timezone.utc)
    return f"uploads/{user_id}/{now.strftime('%Y/%m/%d')}/{import_job_id}.pdf"


def validate_pdf_content(filename: str, content: bytes) -> None:
    """Validate uploaded PDF bytes and filename."""
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are accepted")
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise ValueError("File size exceeds 50MB limit")
    if not content.startswith(b"%PDF-"):
        raise ValueError("File is not a valid PDF")


async def read_uploaded_pdf(file: UploadFile) -> tuple[bytes, str]:
    """Read and validate an uploaded PDF file."""
    if not file:
        raise ValueError("No file uploaded")

    filename = file.filename or "untitled.pdf"
    content = await file.read()
    validate_pdf_content(filename, content)
    return content, filename


async def save_content_to_storage_key(storage_key: str, content: bytes) -> Path:
    """Persist uploaded bytes to the local storage root."""
    file_path = local_storage_root() / storage_key
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "wb") as output_file:
        await output_file.write(content)

    return file_path


async def resolve_or_create_legacy_knowledge_base(
    user_id: str,
    db: AsyncSession,
) -> KnowledgeBase:
    """Resolve the user's oldest KB, creating one for legacy upload compatibility."""
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id)
        .order_by(KnowledgeBase.created_at.asc())
        .limit(1)
    )
    kb = result.scalar_one_or_none()
    if kb:
        return kb

    kb = KnowledgeBase(
        user_id=user_id,
        name=DEFAULT_LEGACY_KB_NAME,
        description=DEFAULT_LEGACY_KB_DESCRIPTION,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    logger.info("Created default KB for legacy upload path", user_id=user_id, kb_id=kb.id)
    return kb


async def attach_uploaded_file_to_job(
    *,
    job: Any,
    user_id: str,
    filename: str,
    content: bytes,
    db: AsyncSession,
) -> dict[str, Any]:
    """Persist uploaded file, attach it to an existing ImportJob, and enqueue processing."""
    validate_pdf_content(filename, content)

    service = ImportJobService()
    storage_key = build_upload_storage_key(user_id, job.id)
    await save_content_to_storage_key(storage_key, content)

    sha256 = hashlib.sha256(content).hexdigest()
    await service.set_file_info(
        job=job,
        storage_key=storage_key,
        sha256=sha256,
        size_bytes=len(content),
        filename=filename,
        mime_type="application/pdf",
        db=db,
    )

    from app.workers.import_worker import process_import_job

    process_import_job.delay(job.id)

    return {
        "importJobId": job.id,
        "storageKey": storage_key,
        "sha256": sha256,
        "sizeBytes": len(content),
        "status": "queued",
        "stage": "uploaded",
        "progress": 10,
    }


async def create_import_job_from_uploaded_file(
    *,
    user_id: str,
    filename: str,
    content: bytes,
    db: AsyncSession,
    kb_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or resolve the target KB, persist the file, and queue ImportJob processing."""
    service = ImportJobService()
    resolved_kb_id = kb_id
    if resolved_kb_id is None:
        resolved_kb = await resolve_or_create_legacy_knowledge_base(user_id, db)
        resolved_kb_id = resolved_kb.id

    job = await service.create_job(
        user_id=user_id,
        kb_id=resolved_kb_id,
        source_type="local_file",
        source_ref_raw=filename,
        options=options or {},
        db=db,
    )

    file_info = await attach_uploaded_file_to_job(
        job=job,
        user_id=user_id,
        filename=filename,
        content=content,
        db=db,
    )
    file_info["knowledgeBaseId"] = resolved_kb_id
    return file_info