"""Paper tool implementations for Agent.

Tools:
- upload_paper: Upload new paper (requires confirmation)
- delete_paper: Delete paper (requires confirmation)

Each tool returns: {success: bool, data: any, error: str?}
"""

from typing import Any, Dict

from app.core.database import get_db_connection
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
    import uuid
    import tempfile
    import httpx
    from app.core.storage import ObjectStorage
    from app.workers.pdf_coordinator import get_pdf_coordinator
    
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
        
        # 4. Create paper record in database
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO papers (id, user_id, title, authors, year, pdf_url, 
                                   arxiv_id, doi, status, created_at, updated_at, storage_key)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW(), NOW(), $9)
            """, paper_id, user_id, metadata.get("title", "Untitled"),
                metadata.get("authors", []), metadata.get("year"),
                paper_url, metadata.get("arxiv_id"), metadata.get("doi"),
                storage_key)
        
        # 5. Create processing task
        task_id = str(uuid.uuid4())
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO processing_tasks (id, paper_id, status, storage_key, created_at, updated_at)
                VALUES ($1, $2, 'pending', $3, NOW(), NOW())
            """, task_id, paper_id, storage_key)
        
        # 6. Trigger PDF processing via PDFCoordinator
        coordinator = get_pdf_coordinator()
        # Process in background (don't await to avoid blocking)
        import asyncio
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

        async with get_db_connection() as conn:
            # Soft delete (mark as deleted)
            result = await conn.execute(
                """
                UPDATE papers
                SET status = 'deleted', updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                """,
                paper_id,
                user_id
            )

            if result == "UPDATE 0":
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