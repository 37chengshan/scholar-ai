"""PDF download worker for external papers.

Downloads PDFs from external sources with fallback and retry logic.
"""
import asyncio
import httpx
from typing import Optional
from datetime import datetime, timezone

from app.utils.logger import logger
from app.database import AsyncSessionLocal
from app.models.paper import Paper
from app.core.storage import store_pdf

PDF_DOWNLOAD_TIMEOUT = 60.0  # seconds
MAX_RETRIES = 2


async def fetch_pdf_with_retry(url: str, timeout: float = PDF_DOWNLOAD_TIMEOUT) -> bytes:
    """Fetch PDF with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content

                # Verify PDF header
                if not content.startswith(b'%PDF'):
                    raise ValueError(f"Downloaded content is not a PDF: {content[:10]}")

                return content
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"PDF download attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            raise


async def update_paper_status(paper_id: str, status: str, error_msg: Optional[str] = None):
    """Update paper status in database.

    Note: error_msg is logged but not stored in Paper model.
    The ProcessingTask model has error_message field for detailed tracking.
    """
    async with AsyncSessionLocal() as db:
        # Fetch and update the paper
        from sqlalchemy import select
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()

        if paper:
            paper.status = status
            paper.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Updated paper {paper_id} status to {status}")

            if error_msg:
                logger.error(f"Paper {paper_id} error: {error_msg}")
        else:
            logger.warning(f"Paper {paper_id} not found for status update")


async def download_external_pdf(
    paper_id: str,
    primary_url: str,
    source: str,
    fallback_url: Optional[str] = None,
    arxiv_id: Optional[str] = None
) -> bool:
    """Download PDF from external source with fallback.

    Args:
        paper_id: Internal paper ID
        primary_url: Primary PDF URL
        source: Source type ('arxiv' or 'semantic-scholar')
        fallback_url: Optional fallback URL
        arxiv_id: Optional arXiv ID for constructing fallback URL

    Returns:
        True if download successful, False otherwise

    Strategy:
    1. Try primary_url
    2. If arxiv source, try arxiv.org/pdf/{arxiv_id}.pdf
    3. If fallback_url provided, try it
    4. Mark as no_pdf if all fail
    """
    urls_to_try = [primary_url]

    # Add arXiv fallback for arxiv papers
    if source == "arxiv" and arxiv_id:
        urls_to_try.append(f"https://arxiv.org/pdf/{arxiv_id}.pdf")

    # Add provided fallback
    if fallback_url and fallback_url not in urls_to_try:
        urls_to_try.append(fallback_url)

    last_error = None

    for url in urls_to_try:
        try:
            logger.info(f"Downloading PDF for paper {paper_id} from {url}")
            pdf_content = await fetch_pdf_with_retry(url)

            # Store PDF
            pdf_key = await store_pdf(paper_id, pdf_content)
            logger.info(f"PDF stored for paper {paper_id}: {pdf_key}")

            # Update status to trigger 6-state pipeline
            await update_paper_status(paper_id, "pending")

            return True

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Failed to download from {url}: {e}")
            continue

    # All attempts failed
    logger.error(f"All PDF download attempts failed for paper {paper_id}: {last_error}")
    await update_paper_status(
        paper_id,
        "no_pdf",
        f"PDF download failed: {last_error}"
    )
    return False


class PDFDownloadWorker:
    """Background worker for processing PDF download tasks."""

    async def process_task(self, task_data: dict) -> bool:
        """Process a PDF download task."""
        return await download_external_pdf(
            paper_id=task_data["paper_id"],
            primary_url=task_data["primary_url"],
            source=task_data["source"],
            fallback_url=task_data.get("fallback_url"),
            arxiv_id=task_data.get("arxiv_id")
        )
