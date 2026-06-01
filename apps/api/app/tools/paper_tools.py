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
import ipaddress
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urlparse

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models import Paper, ProcessingTask
from app.core.storage import ObjectStorage
from app.workers.pdf_coordinator import get_pdf_coordinator
from app.utils.logger import logger


# -- SSRF protection --------------------------------------------------------

ALLOWED_SCHEMES = {"http", "https"}

# RFC 1918 + loopback + link-local + cloud metadata
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918
    ipaddress.ip_network("169.254.0.0/16"),     # link-local / cloud metadata
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]


def _validate_url_for_fetch(url: str) -> None:
    """Validate URL is safe to fetch -- blocks SSRF vectors.

    Raises ValueError with a descriptive message if the URL is rejected.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. "
            f"Only http and https are permitted."
        )

    if not parsed.hostname:
        raise ValueError("URL must have a hostname.")

    # Resolve hostname to IP and check against blocked ranges
    import socket
    try:
        addr_info = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")

    for family, _, _, _, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(
                    f"URL resolves to blocked address {ip} "
                    f"(network {network}). Internal/private addresses are "
                    f"not allowed."
                )


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

        # SSRF protection: validate URL before fetching
        try:
            _validate_url_for_fetch(paper_url)
        except ValueError as ve:
            logger.warning("URL validation failed", url=paper_url, error=str(ve))
            return {"success": False, "error": f"Invalid URL: {ve}", "data": None}

        logger.info("Uploading paper from URL", paper_url=paper_url, user_id=user_id)

        # 1. Download PDF from external URL (redirects limited to same-scheme)
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