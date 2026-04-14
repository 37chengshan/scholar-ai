"""Semantic Scholar source adapter.

Per D-02: S2 paper resolution with openAccessPdf.
Per D-07: S2 API uses 1 rps + exponential backoff.
Per gpt意见.md Section 4.2: S2 adapter rules.

Input formats supported:
- paperId (40-char hex)
- CorpusId:xxxxx
- DOI
- arXiv ID
- https://www.semanticscholar.org/paper/{paperId}
"""

import json
import re
from typing import Dict, Optional

from app.core.semantic_scholar_service import SemanticScholarService
from app.services.source_adapters.base_adapter import (
    BaseSourceAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.services.import_rate_limiter import get_s2_import_limiter, get_import_cache
from app.utils.logger import logger


# Regex patterns for S2 input parsing
S2_URL_PATTERN = r"semanticscholar\.org/paper/([a-f0-9]{40})"
S2_PAPER_ID_PATTERN = r"^([a-f0-9]{40})$"
CORPUS_ID_PATTERN = r"^CorpusId:(\d+)$"


class S2Adapter(BaseSourceAdapter):
    """Semantic Scholar source adapter.

    Uses SemanticScholarService (core domain) for API calls.
    Uses import domain rate limiter (1rps) for throttling.
    Checks openAccessPdf for PDF availability.
    """

    def __init__(self):
        self.s2_service = SemanticScholarService()

    def _parse_paper_id(self, input: str) -> Dict[str, Optional[str]]:
        """Parse paper ID from various input formats.

        Args:
            input: User input (paperId, URL, CorpusId, DOI, arXiv ID)

        Returns:
            Dict with paper_id, lookup_type, lookup_value, or error
        """
        input = input.strip()

        # Try URL pattern
        url_match = re.search(S2_URL_PATTERN, input, re.IGNORECASE)
        if url_match:
            return {"paper_id": url_match.group(1)}

        # Try direct paper ID (40-char hex)
        id_match = re.match(S2_PAPER_ID_PATTERN, input, re.IGNORECASE)
        if id_match:
            return {"paper_id": input.lower()}

        # Try CorpusId
        corpus_match = re.match(CORPUS_ID_PATTERN, input, re.IGNORECASE)
        if corpus_match:
            return {
                "lookup_type": "corpus_id",
                "lookup_value": corpus_match.group(1),
            }

        # Try DOI (10.xxxx/xxxxx)
        if re.match(r"^10\.\d{4,}/.+$", input):
            return {"lookup_type": "doi", "lookup_value": input}

        # Try arXiv ID (extract from various formats)
        arxiv_match = re.match(
            r"^(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?$", input, re.IGNORECASE
        )
        if arxiv_match:
            return {"lookup_type": "arxiv", "lookup_value": arxiv_match.group(1)}

        return {"error": "Cannot parse Semantic Scholar input"}

    async def resolve(self, input: str) -> SourceResolution:
        """Parse input and return canonical source reference.

        Per gpt意见.md Section 4.2:
        - Parse paperId from URL or direct input
        - Convert CorpusId/DOI/arXiv to paperId via API lookup
        """
        parsed = self._parse_paper_id(input)

        if "error" in parsed:
            return SourceResolution(
                resolved=False,
                source_type="semantic_scholar",
                error_code="INVALID_S2_INPUT",
                error_message=parsed["error"],
            )

        # Direct paper ID
        if "paper_id" in parsed:
            paper_id = parsed["paper_id"]
            return SourceResolution(
                resolved=True,
                source_type="semantic_scholar",
                canonical_id=paper_id,
                external_ids={"s2": paper_id},
            )

        # Need API lookup for CorpusId/DOI/arXiv
        lookup_type = parsed.get("lookup_type")
        lookup_value = parsed.get("lookup_value")

        # Apply rate limiter
        limiter = get_s2_import_limiter()
        await limiter.acquire()

        try:
            # Use S2 search to find paper by DOI or arXiv
            if lookup_type == "doi":
                query = f"DOI:{lookup_value}"
            elif lookup_type == "arxiv":
                query = f"arXiv:{lookup_value}"
            else:
                query = lookup_value

            # Search for paper
            redis_client = None  # Will use import cache instead
            result = await self.s2_service.search_papers(
                query=query, limit=1, redis_client=redis_client
            )

            papers = result.get("data", [])
            if not papers:
                limiter.record_success()
                return SourceResolution(
                    resolved=False,
                    source_type="semantic_scholar",
                    error_code="S2_PAPER_NOT_FOUND",
                    error_message=f"Paper not found for {lookup_type}: {lookup_value}",
                )

            paper_id = papers[0].get("paperId", "")
            limiter.record_success()

            return SourceResolution(
                resolved=True,
                source_type="semantic_scholar",
                canonical_id=paper_id,
                external_ids={"s2": paper_id, lookup_type: lookup_value},
            )

        except Exception as e:
            limiter.record_failure()
            logger.error(
                "S2 lookup failed",
                lookup_type=lookup_type,
                lookup_value=lookup_value,
                error=str(e),
            )
            return SourceResolution(
                resolved=False,
                source_type="semantic_scholar",
                error_code="S2_LOOKUP_FAILED",
                error_message=str(e),
            )

    async def fetch_metadata(self, resolution: SourceResolution) -> MetadataPreview:
        """Get paper metadata from Semantic Scholar.

        Uses SemanticScholarService (core domain).
        Checks openAccessPdf.url for PDF availability.
        """
        if not resolution.resolved:
            return MetadataPreview()

        paper_id = resolution.canonical_id
        if not paper_id:
            return MetadataPreview()

        # Check import cache first
        cache = await get_import_cache()
        cache_key = cache.make_s2_cache_key(paper_id)

        cached = await cache.get(cache_key)
        if cached:
            logger.info("S2 metadata cache hit", paper_id=paper_id)
            data = json.loads(cached)
            return MetadataPreview(
                title=data.get("title"),
                authors=data.get("authors", []),
                year=data.get("year"),
                abstract=data.get("abstract"),
                venue=data.get("venue"),
                pdf_available=data.get("pdf_available", False),
                pdf_source=data.get("pdf_source"),
                citation_count=data.get("citation_count"),
                external_ids=data.get("external_ids", {}),
            )

        # Apply rate limiter
        limiter = get_s2_import_limiter()
        await limiter.acquire()

        try:
            # Get paper details
            redis_client = None  # Use import cache instead of S2's tiered cache
            paper = await self.s2_service.get_paper_details(
                paper_id=paper_id,
                fields="paperId,title,year,authors,abstract,openAccessPdf,citationCount,venue,externalIds",
                redis_client=redis_client,
            )

            limiter.record_success()

            # Extract metadata
            title = paper.get("title", "")
            year = paper.get("year")
            abstract = paper.get("abstract", "")
            venue = paper.get("venue", "")
            citation_count = paper.get("citationCount")

            authors = []
            for author in paper.get("authors", []):
                name = author.get("name")
                if name:
                    authors.append(name)

            # Check openAccessPdf
            open_access = paper.get("openAccessPdf", {}) or {}
            pdf_url = open_access.get("url") if open_access else None
            pdf_available = bool(pdf_url)
            pdf_source = "semantic_scholar" if pdf_available else None

            # Extract external IDs
            external_ids = {"s2": paper_id}
            ext_ids = paper.get("externalIds", {}) or {}
            if ext_ids.get("ArXiv"):
                external_ids["arxiv"] = ext_ids["ArXiv"]
            if ext_ids.get("DOI"):
                external_ids["doi"] = ext_ids["DOI"]

            # Cache result
            cache_data = {
                "title": title,
                "authors": authors,
                "year": year,
                "abstract": abstract,
                "venue": venue,
                "pdf_available": pdf_available,
                "pdf_source": pdf_source,
                "citation_count": citation_count,
                "external_ids": external_ids,
            }
            await cache.set(cache_key, json.dumps(cache_data), ttl_seconds=604800)  # 7 days

            logger.info(
                "S2 metadata fetched",
                paper_id=paper_id,
                title=title[:50] if title else None,
                pdf_available=pdf_available,
            )

            return MetadataPreview(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                venue=venue,
                pdf_available=pdf_available,
                pdf_source=pdf_source,
                citation_count=citation_count,
                external_ids=external_ids,
            )

        except Exception as e:
            limiter.record_failure()
            logger.error(
                "S2 metadata fetch failed",
                paper_id=paper_id,
                error=str(e),
            )
            return MetadataPreview(title=None, pdf_available=False)

    async def acquire_pdf(
        self, resolution: SourceResolution, storage_path: str, storage_key: str
    ) -> str:
        """Download PDF from openAccessPdf URL.

        Raises exception if no openAccessPdf available.
        """
        if not resolution.resolved:
            raise Exception("Source not resolved")

        # Need to fetch metadata to get openAccessPdf URL
        metadata = await self.fetch_metadata(resolution)

        if not metadata.pdf_available:
            raise Exception("NO_OPEN_ACCESS_PDF: This paper has no open access PDF")

        # Get PDF URL from cache or API
        paper_id = resolution.canonical_id
        cache = await get_import_cache()
        cache_key = cache.make_s2_cache_key(paper_id)

        cached = await cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            # Need to re-fetch to get actual URL
            pass

        # Fetch paper details to get PDF URL
        limiter = get_s2_import_limiter()
        await limiter.acquire()

        try:
            paper = await self.s2_service.get_paper_details(
                paper_id=paper_id,
                fields="openAccessPdf",
                redis_client=None,
            )
            limiter.record_success()

            open_access = paper.get("openAccessPdf", {}) or {}
            pdf_url = open_access.get("url")

            if not pdf_url:
                raise Exception("NO_OPEN_ACCESS_PDF: openAccessPdf URL is empty")

        except Exception as e:
            limiter.record_failure()
            raise

        # Apply rate limiter for download
        await limiter.acquire()

        # Download PDF
        import httpx
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
                "S2 PDF downloaded",
                paper_id=paper_id,
                storage_key=storage_key,
                size_bytes=len(content),
            )

            return storage_key

        except Exception as e:
            limiter.record_failure()
            logger.error(
                "S2 PDF download failed",
                paper_id=paper_id,
                error=str(e),
            )
            raise


__all__ = ["S2Adapter"]