"""Semantic Scholar API integration service."""

import httpx
import json
import os
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.logger import logger


class SemanticScholarService:
    """Semantic Scholar Academic Graph API integration.

    Provides batch operations, citation network, and metadata retrieval
    with automatic retry and tiered caching.

    Per D-01: Batch operations support up to 1000 IDs.
    Per D-02: Citation network endpoints return paginated results.
    Per D-10: Tiered TTL caching (24h/7d/30d).
    Per D-12: Automatic retry on rate limits.
    """

    def __init__(self):
        self.api_url = "https://api.semanticscholar.org/graph/v1"
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.headers = {"x-api-key": self.api_key} if self.api_key else {}
        self.timeout = 30.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def batch_get_papers(
        self,
        paper_ids: List[str],
        fields: Optional[str] = None,
        redis_client: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Batch get paper details by IDs.

        Per D-01: Max 1000 IDs, recommended safe batch 500.

        Args:
            paper_ids: List of paper IDs (max 1000)
            fields: Comma-separated fields (default: paperId,title,year,authors,abstract,citationCount,openAccessPdf,publicationDate,venue,referenceCount)
            redis_client: Optional Redis client for caching

        Returns:
            List of paper dicts with requested fields
        """
        if len(paper_ids) > 1000:
            logger.warning("S2 batch limit exceeded", count=len(paper_ids))
            paper_ids = paper_ids[:1000]

        if not fields:
            fields = "paperId,title,year,authors,abstract,citationCount,openAccessPdf,publicationDate,venue,referenceCount"

        # Per D-11: Cache key with sorted IDs
        cache_key = f"s2:batch:{hash(tuple(sorted(paper_ids)))}:{fields}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info("S2 batch cache hit", count=len(paper_ids))
                return json.loads(cached)

        url = f"{self.api_url}/paper/batch"
        params = {"fields": fields}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                params=params,
                json={"ids": paper_ids},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        # Per D-10: Cache for 7 days
        if redis_client:
            await redis_client.setex(cache_key, 604800, json.dumps(data))
            logger.info("S2 batch cached", count=len(paper_ids))

        return data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_citations(
        self,
        paper_id: str,
        fields: Optional[str] = None,
        limit: int = 1000,
        redis_client: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Get citations for a paper (who cited this paper).

        Per D-02: Single depth, default limit 1000.

        Args:
            paper_id: Semantic Scholar paper ID
            fields: Fields to return (default: paperId,title,year,authors)
            limit: Max citations (default 1000)
            redis_client: Optional Redis client

        Returns:
            List of citing papers with metadata
        """
        if not fields:
            fields = "paperId,title,year,authors"

        # Per D-11: Cache key
        cache_key = f"s2:citations:{paper_id}:{limit}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

        url = f"{self.api_url}/paper/{paper_id}/citations"
        params = {"fields": fields, "limit": limit}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", [])

        # Per D-10: Cache for 30 days
        if redis_client:
            await redis_client.setex(cache_key, 2592000, json.dumps(result))

        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_references(
        self,
        paper_id: str,
        fields: Optional[str] = None,
        limit: int = 1000,
        redis_client: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Get references for a paper (papers cited by this paper).

        Per D-02: Single depth, default limit 1000.

        Args:
            paper_id: Semantic Scholar paper ID
            fields: Fields to return (default: paperId,title,year,authors)
            limit: Max references (default 1000)

        Returns:
            List of referenced papers with metadata
        """
        if not fields:
            fields = "paperId,title,year,authors"

        cache_key = f"s2:references:{paper_id}:{limit}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

        url = f"{self.api_url}/paper/{paper_id}/references"
        params = {"fields": fields, "limit": limit}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", [])

        if redis_client:
            await redis_client.setex(cache_key, 2592000, json.dumps(result))

        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_paper_details(
        self,
        paper_id: str,
        fields: Optional[str] = None,
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Get single paper details.

        Args:
            paper_id: Semantic Scholar paper ID
            fields: Comma-separated fields
            redis_client: Optional Redis client

        Returns:
            Paper dict with requested fields
        """
        if not fields:
            fields = "paperId,title,year,authors,abstract,citationCount,openAccessPdf,referenceCount,publicationDate,venue"

        cache_key = f"s2:paper:{paper_id}:{fields}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

        url = f"{self.api_url}/paper/{paper_id}"
        params = {"fields": fields}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # Per D-10: Cache for 7 days
        if redis_client:
            await redis_client.setex(cache_key, 604800, json.dumps(data))

        return data


# Singleton pattern (match existing services)
_s2_service: Optional[SemanticScholarService] = None


def get_semantic_scholar_service() -> SemanticScholarService:
    """Get or create SemanticScholarService singleton."""
    global _s2_service
    if _s2_service is None:
        _s2_service = SemanticScholarService()
    return _s2_service