"""DOI source adapter.

Per D-02: DOI resolution via CrossRef + S2 PDF check.
Per D-07: Uses S2 rate limiter (1rps) for PDF availability check.
Per gpt意见.md Section 4.3: DOI adapter rules.

Input formats supported:
- 10.1038/nature12373
- doi:10.1038/nature12373
- https://doi.org/10.1038/nature12373
"""

import re
from typing import Dict, Optional

import httpx

from app.core.crossref_service import CrossRefService
from app.core.semantic_scholar_service import SemanticScholarService
from app.services.source_adapters.base_adapter import (
    BaseSourceAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.services.import_rate_limiter import get_s2_import_limiter, get_import_cache
from app.utils.logger import logger


# Regex patterns for DOI parsing
DOI_PATTERN = r"^10\.\d{4,}/.+$"
DOI_URL_PATTERN = r"doi\.org/(10\.\d{4,}/.+)"
DOI_PREFIX_PATTERN = r"^doi:"


class DoiAdapter(BaseSourceAdapter):
    """DOI source adapter.

    Uses CrossRefService (core domain) for metadata.
    Uses SemanticScholarService (core domain) for PDF availability check.
    Uses import domain rate limiter for S2 calls.
    """

    def __init__(self):
        self.crossref_service = CrossRefService()
        self.s2_service = SemanticScholarService()

    def _normalize_doi(self, input: str) -> Optional[str]:
        """Normalize DOI from various input formats.

        Args:
            input: User input (DOI, URL, etc.)

        Returns:
            Normalized DOI (e.g., "10.1038/nature12373")
        """
        input = input.strip().lower()

        # Remove doi: prefix
        if re.match(DOI_PREFIX_PATTERN, input, re.IGNORECASE):
            input = re.sub(DOI_PREFIX_PATTERN, "", input, flags=re.IGNORECASE)

        # Extract from URL
        url_match = re.search(DOI_URL_PATTERN, input, re.IGNORECASE)
        if url_match:
            return url_match.group(1)

        # Direct DOI
        if re.match(DOI_PATTERN, input):
            return input

        return None

    async def resolve(self, input: str) -> SourceResolution:
        """Parse input and return canonical source reference.

        Per gpt意见.md Section 4.3:
        - Normalize DOI format
        - Validate DOI format (10.xxxx/xxxxx)
        """
        doi = self._normalize_doi(input)

        if not doi:
            return SourceResolution(
                resolved=False,
                source_type="doi",
                error_code="INVALID_DOI_FORMAT",
                error_message="Cannot parse DOI from input",
            )

        return SourceResolution(
            resolved=True,
            source_type="doi",
            canonical_id=doi,
            external_ids={"doi": doi},
        )

    async def fetch_metadata(self, resolution: SourceResolution) -> MetadataPreview:
        """Get paper metadata from CrossRef and check S2 for PDF.

        Per gpt意见.md Section 4.3:
        - First call CrossRef for metadata
        - Then check S2 for openAccessPdf
        """
        if not resolution.resolved:
            return MetadataPreview()

        doi = resolution.canonical_id
        if not doi:
            return MetadataPreview()

        # Get metadata from CrossRef (no rate limit needed for CrossRef)
        try:
            import redis.asyncio as redis
            from app.config import settings

            redis_client = redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_connect_timeout=5
            )
            crossref_result = await self.crossref_service.resolve_doi(doi, redis_client)

            title = crossref_result.get("title", "")
            authors = crossref_result.get("authors", [])
            year = crossref_result.get("year")
            abstract = crossref_result.get("abstract", "")
            venue = None  # CrossRef doesn't always have venue

            logger.info("DOI metadata from CrossRef", doi=doi, title=title[:50] if title else None)

        except Exception as e:
            logger.error("CrossRef lookup failed", doi=doi, error=str(e))
            # Continue with empty metadata, will try S2
            title = None
            authors = []
            year = None
            abstract = None
            venue = None

        # Check S2 for PDF availability
        pdf_available = False
        pdf_source = None

        # Apply import rate limiter for S2
        limiter = get_s2_import_limiter()
        await limiter.acquire()

        try:
            # Search S2 by DOI
            result = await self.s2_service.search_papers(
                query=f"DOI:{doi}",
                limit=1,
                redis_client=None,  # Use import cache instead
            )

            papers = result.get("data", [])
            if papers:
                paper = papers[0]
                open_access = paper.get("openAccessPdf", {}) or {}
                pdf_url = open_access.get("url") if open_access else None

                if pdf_url:
                    pdf_available = True
                    pdf_source = "semantic_scholar"

                # Use S2 metadata if CrossRef failed
                if not title:
                    title = paper.get("title", "")
                if not year:
                    year = paper.get("year")
                if not authors:
                    authors = [
                        a.get("name") for a in paper.get("authors", []) if a.get("name")
                    ]

            limiter.record_success()

        except Exception as e:
            limiter.record_failure()
            logger.warning("S2 DOI lookup failed", doi=doi, error=str(e))

        return MetadataPreview(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            venue=venue,
            pdf_available=pdf_available,
            pdf_source=pdf_source,
            external_ids={"doi": doi},
        )

    async def acquire_pdf(
        self, resolution: SourceResolution, storage_path: str, storage_key: str
    ) -> str:
        """Download PDF from S2 openAccessPdf if available.

        Raises exception if no PDF available.
        """
        if not resolution.resolved:
            raise Exception("Source not resolved")

        doi = resolution.canonical_id

        # Check S2 for openAccessPdf URL
        limiter = get_s2_import_limiter()
        await limiter.acquire()

        try:
            result = await self.s2_service.search_papers(
                query=f"DOI:{doi}",
                limit=1,
                redis_client=None,
            )

            papers = result.get("data", [])
            if not papers:
                raise Exception("DOI_NO_PDF: Paper not found in Semantic Scholar")

            paper = papers[0]
            open_access = paper.get("openAccessPdf", {}) or {}
            pdf_url = open_access.get("url")

            if not pdf_url:
                raise Exception("DOI_NO_PDF: No open access PDF available")

            limiter.record_success()

        except Exception as e:
            if "DOI_NO_PDF" in str(e):
                raise
            limiter.record_failure()
            raise Exception(f"DOI_NO_PDF: S2 lookup failed - {str(e)}")

        # Apply rate limiter for download
        await limiter.acquire()

        # Download PDF
        import os

        try:
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()

                content = response.content

                # Validate magic bytes
                if not content.startswith(b"%PDF-"):
                    raise Exception("Downloaded file is not a valid PDF")

                limiter.record_success()

            # Write to storage
            full_path = os.path.join(storage_path, storage_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(content)

            logger.info(
                "DOI PDF downloaded via S2",
                doi=doi,
                storage_key=storage_key,
                size_bytes=len(content),
            )

            return storage_key

        except Exception as e:
            limiter.record_failure()
            logger.error("DOI PDF download failed", doi=doi, error=str(e))
            raise


__all__ = ["DoiAdapter"]