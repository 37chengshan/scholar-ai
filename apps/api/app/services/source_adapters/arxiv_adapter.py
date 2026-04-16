"""arXiv source adapter.

Per D-02: arXiv ID/URL resolution and PDF download.
Per D-07: arXiv API uses 3 second interval + result caching.
Per gpt意见.md Section 4.1: arXiv adapter rules.

Input formats supported:
- 2501.01234
- 2501.01234v2
- arXiv:2501.01234
- https://arxiv.org/abs/2501.01234
- https://arxiv.org/pdf/2501.01234.pdf
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict

import httpx

from app.services.source_adapters.base_adapter import (
    BaseSourceAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.services.import_rate_limiter import (
    get_arxiv_import_limiter,
    get_import_cache,
)
from app.utils.logger import logger


# Regex patterns for arXiv ID parsing
# Per gpt意见.md Section 4.1: Support various input formats
ARXIV_ID_PATTERN = r"^(?:arXiv:)?(\d{4}\.\d{4,5})(v(\d+))?$"
ARXIV_URL_PATTERN = r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v(\d+))?(?:\.pdf)?$"


class ArxivAdapter(BaseSourceAdapter):
    """arXiv source adapter with import domain rate limiting.

    Uses 3 second interval between requests per D-07.
    Cache results for 1 day per D-07.
    """

    def __init__(self):
        self.api_url = "https://export.arxiv.org/api/query"
        self.timeout = 30.0

    def _parse_arxiv_id(self, input: str) -> Dict[str, Any]:
        """Parse arXiv ID from various input formats.

        Args:
            input: User input (ID, URL, etc.)

        Returns:
            Dict with base_id, version, or error info
        """
        # Try URL pattern first
        url_match = re.search(ARXIV_URL_PATTERN, input, re.IGNORECASE)
        if url_match:
            base_id = url_match.group(1)
            version = int(url_match.group(2)) if url_match.group(2) else None
            return {"base_id": base_id, "version": version}

        # Try ID pattern
        id_match = re.match(ARXIV_ID_PATTERN, input.strip(), re.IGNORECASE)
        if id_match:
            base_id = id_match.group(1)
            version = int(id_match.group(3)) if id_match.group(3) else None
            return {"base_id": base_id, "version": version}

        return {"error": "Cannot parse arXiv ID from input"}

    async def resolve(self, input: str) -> SourceResolution:
        """Parse input and return canonical source reference.

        Per gpt意见.md Section 4.1:
        - Extract base ID and optional version
        - Generate canonical abs and PDF URLs
        - Store version for later use
        """
        parsed = self._parse_arxiv_id(input)

        if "error" in parsed:
            return SourceResolution(
                resolved=False,
                source_type="arxiv",
                error_code="INVALID_ARXIV_ID",
                error_message=parsed["error"],
            )

        base_id = parsed["base_id"]
        version = parsed.get("version")

        # Build canonical ID
        if version:
            canonical_id = f"{base_id}v{version}"
        else:
            canonical_id = base_id  # Latest version

        # Build URLs
        canonical_abs_url = f"https://arxiv.org/abs/{canonical_id}"
        canonical_pdf_url = f"https://arxiv.org/pdf/{canonical_id}.pdf"

        return SourceResolution(
            resolved=True,
            source_type="arxiv",
            canonical_id=canonical_id,
            canonical_pdf_url=canonical_pdf_url,
            version=version,
            external_ids={"arxiv": base_id},
        )

    async def fetch_metadata(self, resolution: SourceResolution) -> MetadataPreview:
        """Get paper metadata from arXiv API.

        Uses Atom XML response format.
        Caches results for 1 day.
        Applies import domain rate limiter (3s interval).
        """
        if not resolution.resolved:
            return MetadataPreview()

        # Extract base ID for API query
        base_id = resolution.external_ids.get("arxiv", "")
        if not base_id:
            return MetadataPreview(pdf_available=True, pdf_source="arxiv")

        # Check cache first
        cache = await get_import_cache()
        cache_key = cache.make_arxiv_cache_key(base_id)

        cached = await cache.get(cache_key)
        if cached:
            logger.info("arXiv metadata cache hit", arxiv_id=base_id)
            data = json.loads(cached)
            return MetadataPreview(
                title=data.get("title"),
                authors=data.get("authors", []),
                year=data.get("year"),
                abstract=data.get("abstract"),
                venue="arXiv",
                pdf_available=True,
                pdf_source="arxiv",
                external_ids={"arxiv": base_id},
            )

        # Apply rate limiter
        limiter = get_arxiv_import_limiter()
        await limiter.acquire()

        # Query arXiv API
        params = {"id_list": base_id, "max_results": 1}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.api_url, params=params)

                if response.status_code == 429:
                    logger.warning("arXiv API rate limited", arxiv_id=base_id)
                    limiter.record_failure()
                    return MetadataPreview(
                        title=None,
                        pdf_available=True,
                        pdf_source="arxiv",
                    )

                response.raise_for_status()
                limiter.record_success()

            # Parse Atom XML response
            root = ET.fromstring(response.text)

            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            # Find entry
            entry = root.find("atom:entry", ns)
            if entry is None:
                logger.warning("arXiv entry not found", arxiv_id=base_id)
                return MetadataPreview(
                    title=None,
                    pdf_available=True,
                    pdf_source="arxiv",
                )

            # Extract metadata
            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name)

            published = entry.findtext("atom:published", "", ns)
            year = int(published[:4]) if published and len(published) >= 4 else None

            # Cache result
            cache_data = {
                "title": title,
                "authors": authors,
                "year": year,
                "abstract": summary,
            }
            await cache.set(cache_key, json.dumps(cache_data), ttl_seconds=86400)

            logger.info("arXiv metadata fetched", arxiv_id=base_id, title=title[:50])

            return MetadataPreview(
                title=title,
                authors=authors,
                year=year,
                abstract=summary,
                venue="arXiv",
                pdf_available=True,
                pdf_source="arxiv",
                external_ids={"arxiv": base_id},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "arXiv API HTTP error",
                arxiv_id=base_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            limiter.record_failure()
            return MetadataPreview(
                title=None,
                pdf_available=True,
                pdf_source="arxiv",
            )
        except Exception as e:
            logger.error(
                "arXiv metadata fetch failed",
                arxiv_id=base_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return MetadataPreview(
                title=None,
                pdf_available=True,
                pdf_source="arxiv",
            )

    async def acquire_pdf(
        self, resolution: SourceResolution, storage_path: str, storage_key: str
    ) -> str:
        """Download PDF from arXiv.

        Applies import domain rate limiter before download.
        Validates PDF magic bytes after download.
        """
        if not resolution.resolved or not resolution.canonical_pdf_url:
            raise Exception("No PDF URL available for arXiv source")

        # Apply rate limiter
        limiter = get_arxiv_import_limiter()
        await limiter.acquire()

        # Download PDF
        try:
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                response = await client.get(resolution.canonical_pdf_url)
                response.raise_for_status()

                content = response.content

                # Validate magic bytes
                if not content.startswith(b"%PDF-"):
                    limiter.record_failure()
                    raise Exception("Downloaded file is not a valid PDF")

                limiter.record_success()

            # Write to storage
            import os
            full_path = os.path.join(storage_path, storage_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(content)

            logger.info(
                "arXiv PDF downloaded",
                arxiv_id=resolution.canonical_id,
                storage_key=storage_key,
                size_bytes=len(content),
            )

            return storage_key

        except Exception as e:
            limiter.record_failure()
            logger.error(
                "arXiv PDF download failed",
                arxiv_id=resolution.canonical_id,
                error=str(e),
            )
            raise


__all__ = ["ArxivAdapter"]