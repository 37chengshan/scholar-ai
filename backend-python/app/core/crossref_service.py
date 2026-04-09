"""CrossRef DOI resolution service.

Provides:
- CrossRefService: Resolve DOI to paper metadata via CrossRef REST API
- Redis caching (24h TTL) for DOI results
- Error handling for invalid DOI and API failures

Requirements:
- SEARCH-03: CrossRef DOI resolution
"""

import json
import httpx
from typing import Any, Dict, Optional

from app.config import settings
from app.utils.logger import logger


class CrossRefService:
    """CrossRef API integration for DOI resolution.

    Attributes:
        api_url: CrossRef REST API base URL
        headers: Polite User-Agent header (required by CrossRef)
        timeout: HTTP request timeout (20 seconds)
    """

    def __init__(self):
        """Initialize CrossRefService with API configuration."""
        self.api_url = "https://api.crossref.org/works/"
        self.headers = {
            "User-Agent": "ScholarAI/1.0 (mailto:contact@scholarai.com)"
        }
        self.timeout = 20.0

    async def resolve_doi(
        self,
        doi: str,
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Resolve DOI to paper metadata via CrossRef API.

        Args:
            doi: DOI identifier (e.g., "10.1038/nature12373")
            redis_client: Optional Redis client for caching

        Returns:
            Dictionary with paper metadata:
            - id: DOI string
            - title: Paper title
            - authors: List of author names
            - year: Publication year
            - abstract: Paper abstract (or "No abstract available")
            - source: "crossref"
            - url: DOI.org URL
            - citationCount: None (CrossRef doesn't provide)

        Raises:
            HTTPException: 404 if DOI not found, 500 if API error

        Example:
            >>> service = CrossRefService()
            >>> result = await service.resolve_doi("10.1038/nature12373")
            >>> result["title"]
            "The DNA sequence of the human genome"
        """
        from fastapi import HTTPException

        # Check cache first (24h TTL, same as other searches)
        cache_key = f"search:doi:{doi}"
        if redis_client:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info("DOI cache hit", doi=doi)
                    return json.loads(cached)
            except Exception as e:
                logger.warning("Redis cache get failed", doi=doi, error=str(e))

        # Call CrossRef API
        url = f"{self.api_url}{doi}"
        logger.info("CrossRef API call", doi=doi, url=url)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 404:
                    logger.warning("DOI not found", doi=doi)
                    raise HTTPException(
                        status_code=404,
                        detail=f"DOI not found: {doi}"
                    )

                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            logger.error("CrossRef API timeout", doi=doi)
            raise HTTPException(
                status_code=504,
                detail="CrossRef API timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error("CrossRef API error", doi=doi, status=e.response.status_code)
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"CrossRef API error: {str(e)}"
            )

        # Parse CrossRef JSON response
        message = data.get("message", {})

        # Extract title (CrossRef returns array)
        title_list = message.get("title", [])
        title = title_list[0] if title_list else "Unknown Title"

        # Extract authors
        authors = []
        for author in message.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        # Extract year from published-print or published-online
        year = 0
        published = message.get("published-print") or message.get("published-online")
        if published:
            date_parts = published.get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0] if date_parts[0] else 0

        # Extract abstract (may be empty)
        abstract = message.get("abstract", "No abstract available")

        # Construct result dictionary (match SearchResult model)
        result = {
            "id": doi,
            "title": title,
            "authors": authors,
            "year": year,
            "abstract": abstract,
            "source": "crossref",
            "url": f"https://doi.org/{doi}",
            "citationCount": None,
            "pdfUrl": None,
            "arxivId": None,
        }

        # Cache result (24h TTL)
        if redis_client:
            try:
                await redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(result)
                )
                logger.info("DOI cached", doi=doi, cache_key=cache_key)
            except Exception as e:
                logger.warning("Redis cache set failed", doi=doi, error=str(e))

        return result