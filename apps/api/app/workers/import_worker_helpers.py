"""Helper utilities for import worker orchestration.

Extracted from import_worker.py to keep worker entrypoints focused on
state transitions and task coordination.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.models.paper import Paper
from app.models.upload_history import UploadHistory
from app.services.source_adapters import (
    ArxivAdapter,
    S2Adapter,
    DoiAdapter,
    PdfUrlAdapter,
)
from app.utils.logger import logger


def get_adapter(source_type: str):
    """Get source adapter by type."""
    adapters = {
        "arxiv": ArxivAdapter(),
        "semantic_scholar": S2Adapter(),
        "doi": DoiAdapter(),
        "pdf_url": PdfUrlAdapter(),
    }
    return adapters.get(source_type)


async def set_resolution(service, job, resolution, db):
    """Store source resolution on ImportJob fields."""
    job.source_ref_normalized = resolution.canonical_id

    if resolution.external_ids:
        job.external_ids = resolution.external_ids

        if resolution.external_ids.get("arxiv"):
            job.external_source = "arxiv"
            job.external_paper_id = resolution.external_ids["arxiv"]
            job.external_version = str(resolution.version) if resolution.version else None
        elif resolution.external_ids.get("doi"):
            job.external_source = "doi"
            job.external_paper_id = resolution.external_ids["doi"]
        elif resolution.external_ids.get("s2"):
            job.external_source = "s2"
            job.external_paper_id = resolution.external_ids["s2"]

    await db.commit()


async def set_metadata(service, job, metadata, db):
    """Store resolved metadata on ImportJob fields."""
    if metadata:
        job.resolved_title = metadata.title
        job.resolved_authors = metadata.authors
        job.resolved_year = metadata.year
        job.resolved_abstract = metadata.abstract
        job.resolved_venue = metadata.venue

        if metadata.external_ids:
            if job.external_ids:
                job.external_ids = {**job.external_ids, **metadata.external_ids}
            else:
                job.external_ids = metadata.external_ids

    await db.commit()


async def compute_hash(storage_key: str) -> str:
    """Compute SHA256 hash of file."""
    base_path = Path(os.getenv("LOCAL_STORAGE_PATH", "./uploads")).resolve()
    file_path = (base_path / storage_key).resolve()
    file_path.relative_to(base_path)

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


async def create_paper_from_job(job, db) -> str:
    """Create Paper entity from ImportJob data."""
    paper_id = str(uuid.uuid4())

    base_title = (job.resolved_title or job.source_ref_raw or "Untitled").strip()
    if not base_title:
        base_title = "Untitled"
    safe_title = await _ensure_unique_paper_title(db, job.user_id, base_title)

    paper = Paper(
        id=paper_id,
        user_id=job.user_id,
        title=safe_title,
        authors=job.resolved_authors or [],
        year=job.resolved_year,
        abstract=job.resolved_abstract,
        venue=job.resolved_venue,
        storage_key=job.storage_key,
        status="processing",
        knowledge_base_id=job.knowledge_base_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    if job.external_ids:
        paper.doi = job.external_ids.get("doi")
        paper.arxiv_id = job.external_ids.get("arxiv")
        paper.s2_paper_id = job.external_ids.get("s2")

    db.add(paper)
    await db.commit()

    history_result = await db.execute(
        select(UploadHistory).where(
            UploadHistory.user_id == job.user_id,
            UploadHistory.paper_id == paper_id,
        )
    )
    history = history_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    filename = job.filename or job.source_ref_raw or "untitled.pdf"

    if history:
        history.filename = filename
        history.status = "PROCESSING"
        history.error_message = None
        history.updated_at = now
    else:
        db.add(
            UploadHistory(
                user_id=job.user_id,
                paper_id=paper_id,
                filename=filename,
                status="PROCESSING",
                created_at=now,
                updated_at=now,
            )
        )

    await db.commit()

    logger.info(f"Paper {paper_id} created from ImportJob {job.id}")
    return paper_id


async def _ensure_unique_paper_title(db, user_id: str, base_title: str) -> str:
    """Ensure title uniqueness under unique_user_title constraint."""
    candidate = base_title.strip() or "Untitled"

    existing = await db.execute(
        select(Paper.id).where(
            Paper.user_id == user_id,
            Paper.title == candidate,
        )
    )
    if existing.scalar_one_or_none() is None:
        return candidate

    for idx in range(2, 100):
        suffix = f" (v{idx})"
        next_candidate = f"{candidate}{suffix}"
        exists = await db.execute(
            select(Paper.id).where(
                Paper.user_id == user_id,
                Paper.title == next_candidate,
            )
        )
        if exists.scalar_one_or_none() is None:
            return next_candidate

    return f"{candidate} ({str(uuid.uuid4())[:8]})"


async def attach_paper_to_kb(job, paper_id: str, db):
    """Attach paper to knowledge base.

    Note: Paper.knowledge_base_id is set in create_paper_from_job().
    """
    logger.info(
        f"Paper {paper_id} uses KB {job.knowledge_base_id} (set in create_paper_from_job)",
        import_job_id=job.id,
    )
