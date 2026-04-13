"""KB Import operations - Upload PDF, import from URL/arXiv, manage papers.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分.

Endpoints:
- POST /api/v1/knowledge-bases/{kb_id}/upload - Upload PDF to KB
- POST /api/v1/knowledge-bases/{kb_id}/import-url - Import from URL/DOI
- POST /api/v1/knowledge-bases/{kb_id}/import-arxiv - Import from arXiv
- POST /api/v1/knowledge-bases/{kb_id}/batch-upload - Batch upload
- POST /api/v1/knowledge-bases/{kb_id}/papers - Add paper to KB
- DELETE /api/v1/knowledge-bases/{kb_id}/papers/{paper_id} - Remove paper from KB
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.paper import Paper
from app.models.task import ProcessingTask
from app.models.upload_history import UploadHistory
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints."""

    success: bool = True
    data: Dict[str, Any]


class KBPaperAdd(BaseModel):
    """Request to add paper to KB."""

    paperId: str


class KBImportUrl(BaseModel):
    """Request to import paper from URL/DOI."""

    url: str


class KBImportArxiv(BaseModel):
    """Request to import paper from arXiv."""

    arxivId: str


# =============================================================================
# KB Paper Management
# =============================================================================


@router.post("/{kb_id}/papers", response_model=KBResponse)
async def add_paper_to_kb(
    kb_id: str,
    request: KBPaperAdd,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Add an existing paper to a knowledge base."""
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Verify paper ownership
        paper_result = await db.execute(
            select(Paper).where(Paper.id == request.paperId, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

        # Update paper's KB
        paper.knowledge_base_id = kb_id
        kb.paper_count += 1

        await db.flush()

        logger.info("Paper added to KB", paper_id=request.paperId, kb_id=kb_id)

        return KBResponse(
            success=True,
            data={
                "paperId": request.paperId,
                "knowledgeBaseId": kb_id,
                "paperCount": kb.paper_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add paper to KB", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to add paper: {str(e)}"),
        )


@router.delete("/{kb_id}/papers/{paper_id}", response_model=KBResponse)
async def remove_paper_from_kb(
    kb_id: str,
    paper_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Remove a paper from a knowledge base."""
    try:
        # Verify KB ownership
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        # Verify paper in this KB
        paper_result = await db.execute(
            select(Paper).where(
                Paper.id == paper_id,
                Paper.knowledge_base_id == kb_id,
                Paper.user_id == user_id,
            )
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found in this knowledge base"),
            )

        # Remove paper from KB
        paper.knowledge_base_id = None
        kb.paper_count -= 1

        await db.flush()

        logger.info("Paper removed from KB", paper_id=paper_id, kb_id=kb_id)

        return KBResponse(
            success=True,
            data={
                "paperId": paper_id,
                "removed": True,
                "paperCount": kb.paper_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove paper from KB", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to remove paper: {str(e)}"),
        )


# =============================================================================
# KB Import Endpoints
# =============================================================================


@router.post("/{kb_id}/upload", response_model=KBResponse)
async def upload_pdf_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF to a knowledge base.

    Per D-08: Paper inherits KB config (embeddingModel, parseEngine, etc.).
    No config fields in request - KB config is used for processing.
    """
    try:
        kb_result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
            )
        )
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Knowledge base not found"),
            )

        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(
                    "No file uploaded. Use form field name 'file'"
                ),
            )

        filename = file.filename or "untitled.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Only PDF files are accepted"),
            )

        content = await file.read()
        file_size = len(content)
        max_size = 50 * 1024 * 1024

        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=Errors.validation("File size exceeds 50MB limit"),
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("File is not a valid PDF"),
            )

        title = filename.replace(".pdf", "").replace(".PDF", "")
        existing_query = select(Paper).where(
            Paper.user_id == user_id,
            Paper.title == title,
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=Errors.conflict(
                    f'A paper with title "{title}" already exists in your library.'
                ),
            )

        storage_key = (
            f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"
        )
        local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./uploads")
        file_path = os.path.join(local_storage_path, storage_key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        async with aiofiles.open(file_path, "wb") as output_file:
            await output_file.write(content)

        paper_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        paper = Paper(
            id=paper_id,
            title=title,
            authors=[],
            status="processing",
            user_id=user_id,
            storage_key=storage_key,
            file_size=file_size,
            keywords=[],
            knowledge_base_id=kb_id,
            upload_status="processing",
            upload_progress=0,
            uploaded_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(paper)

        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=storage_key,
            created_at=now,
            updated_at=now,
        )
        db.add(task)

        upload_history = UploadHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            paper_id=paper_id,
            filename=filename,
            status="PROCESSING",
            created_at=now,
            updated_at=now,
        )
        db.add(upload_history)

        kb.paper_count += 1
        kb.updated_at = now

        logger.info(
            "Paper uploaded directly to knowledge base",
            user_id=user_id,
            kb_id=kb_id,
            paper_id=paper_id,
            filename=filename,
            file_size=file_size,
        )

        return KBResponse(
            success=True,
            data={
                "kbId": kb_id,
                "paperId": paper_id,
                "taskId": task_id,
                "status": "processing",
                "message": "File uploaded successfully. Processing started.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to upload PDF to knowledge base", error=str(e), kb_id=kb_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to upload PDF: {str(e)}"),
        )


@router.post("/{kb_id}/import-url", response_model=KBResponse)
async def import_from_url(
    kb_id: str,
    request: KBImportUrl,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from URL/DOI.

    Per D-08: Paper inherits KB config. Request contains only url field.
    Processing uses KB's stored embedding_model, parse_engine, etc.
    """
    # Stub - will fetch KB and use kb config for processing
    return KBResponse(
        success=True,
        data={"message": "Import URL endpoint - to be implemented", "url": request.url},
    )


@router.post("/{kb_id}/import-arxiv", response_model=KBResponse)
async def import_from_arxiv(
    kb_id: str,
    request: KBImportArxiv,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Import paper from arXiv.

    Per D-08: Paper inherits KB config. Request contains only arxivId field.
    Processing uses KB's stored embedding_model, parse_engine, etc.
    """
    # Stub - will fetch KB and use kb config for processing
    return KBResponse(
        success=True,
        data={
            "message": "Import arXiv endpoint - to be implemented",
            "arxivId": request.arxivId,
        },
    )


@router.post("/{kb_id}/batch-upload", response_model=KBResponse)
async def batch_upload_to_kb(
    kb_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Batch upload PDFs to a knowledge base.

    Per D-08: All papers inherit KB config. No config fields in request.
    """
    # Stub - will fetch KB and use kb config for all paper processing
    return KBResponse(
        success=True,
        data={"message": "Batch upload endpoint - to be implemented", "kbId": kb_id},
    )


__all__ = ["router"]
