"""Paper tool implementations for Agent.

Tools:
- upload_paper: Upload new paper (requires confirmation)
- delete_paper: Delete paper (requires confirmation)

Each tool returns: {success: bool, data: any, error: str?}
"""

import uuid
import tempfile
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models import Paper, ProcessingTask
from app.core.storage import ObjectStorage
from app.workers.pdf_coordinator import get_pdf_coordinator
from app.utils.logger import logger


async def execute_upload_paper(
    params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    Upload a new paper to the library.

    Args:
        params: {
            "paper_url": str,  # PDF URL from search results
            "metadata": {
                "title": str,
                "authors": [str],
                "year": int,
                "source": "arxiv" | "semantic_scholar" | "crossref",
                "arxiv_id": str?,
                "doi": str?
            }
        }
        **kwargs: user_id, session_id

    Returns:
        {success: bool, data: {paper_id: str}, error: str?}
    """
    user_id = kwargs.get("user_id", "")

    try:
        paper_url = params.get("paper_url")
        metadata = params.get("metadata", {})

        if not paper_url:
            return {"success": False, "error": "paper_url is required", "data": None}

        logger.info("Uploading paper from URL", paper_url=paper_url, user_id=user_id)

        # 1. Download PDF from external URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(paper_url, follow_redirects=True)
            response.raise_for_status()

        # 2. Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # 3. Upload to object storage
        storage = ObjectStorage()
        paper_id = str(uuid.uuid4())
        storage_key = f"{user_id}/{paper_id}.pdf"
        await storage.upload_file(storage_key, tmp_path, content_type="application/pdf")

        logger.info("PDF uploaded to storage", storage_key=storage_key)

        # 4. Create paper record in database using SQLAlchemy ORM
        task_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            # Create Paper instance
            paper = Paper(
                id=paper_id,
                user_id=user_id,
                title=metadata.get("title", "Untitled"),
                authors=metadata.get("authors", []),
                year=metadata.get("year"),
                pdf_url=paper_url,
                arxiv_id=metadata.get("arxiv_id"),
                doi=metadata.get("doi"),
                status="pending",
                storage_key=storage_key,
            )
            db.add(paper)

            # Create ProcessingTask instance
            processing_task = ProcessingTask(
                id=task_id,
                paper_id=paper_id,
                status="pending",
                storage_key=storage_key,
            )
            db.add(processing_task)

            await db.commit()

        # 5. Trigger PDF processing via PDFCoordinator
        coordinator = get_pdf_coordinator()
        # Process in background (don't await to avoid blocking)
        asyncio.create_task(coordinator.process(task_id))

        logger.info("Paper uploaded and processing started",
                   paper_id=paper_id, task_id=task_id, user_id=user_id)

        return {
            "success": True,
            "data": {
                "paper_id": paper_id,
                "task_id": task_id,
                "status": "processing",
                "message": "Paper uploaded and processing started"
            },
            "error": None
        }

    except Exception as e:
        logger.error("upload_paper failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}


async def execute_delete_paper(
    params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Execute delete_paper tool.

    Marks paper as deleted (soft delete).

    Args:
        params: {"paper_id": str}
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {deleted: bool}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        paper_id = params.get("paper_id")

        if not paper_id:
            return {"success": False, "error": "Paper ID is required", "data": None}

        logger.info("Delete paper initiated", paper_id=paper_id, user_id=user_id)

        async with AsyncSessionLocal() as db:
            # Update paper status to deleted (soft delete)
            result = await db.execute(
                update(Paper)
                .where(Paper.id == paper_id, Paper.user_id == user_id)
                .values(status="deleted", updated_at=datetime.now(timezone.utc))
            )
            await db.commit()

            if result.rowcount == 0:
                return {
                    "success": False,
                    "error": "Paper not found or access denied",
                    "data": None
                }

        logger.info("Paper deleted", paper_id=paper_id, user_id=user_id)

        return {
            "success": True,
            "data": {"deleted": True},
            "error": None
        }

    except Exception as e:
        logger.error("Delete paper failed", error=str(e), paper_id=params.get("paper_id"))
        return {"success": False, "error": str(e), "data": None}