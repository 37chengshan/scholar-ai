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
    async def search_papers(
        self,
        query: str,
        fields: Optional[str] = None,
        limit: int = 5,
        offset: int = 0,
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Search papers by query string.

        Args:
            query: Search query (title, abstract, authors)
            fields: Comma-separated fields (default: paperId,title,year,authors,abstract,citationCount,venue)
            limit: Max results (default 5 for metadata enrichment per D-09)
            offset: Pagination offset
            redis_client: Optional Redis client for caching

        Returns:
            Dict with 'data' list and 'total' count
        """
        if not fields:
            fields = "paperId,title,year,authors,abstract,citationCount,venue,publicationDate"

        # Per D-11: Cache key format
        cache_key = f"s2:search:{query}:{fields}:{limit}:{offset}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info("S2 search cache hit", query=query[:50])
                return json.loads(cached)

        url = f"{self.api_url}/paper/search"
        params = {"query": query, "fields": fields, "limit": limit, "offset": offset}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # Per D-10: Cache for 24 hours
        if redis_client:
            await redis_client.setex(cache_key, 86400, json.dumps(data))
            logger.info("S2 search cached", query=query[:50])

        return data

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def autocomplete_papers(
        self,
        query: str,
        limit: int = 5,
        redis_client: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Paper autocomplete for search box.

        Per D-01: Trigger at >=3 chars (frontend responsibility)
        Per D-03: Limit to 5 results
        Per D-04: Cache for 1 hour (3600s)

        Args:
            query: Search query string
            limit: Max results (default 5)
            redis_client: Optional Redis client for caching

        Returns:
            List of paper dicts with paperId, title, authors, year
        """
        # Default fields for autocomplete (minimal for speed)
        fields = "paperId,title,year,authors"

        # Cache key per D-11
        cache_key = f"s2:autocomplete:{query}:{limit}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info("S2 autocomplete cache hit", query=query[:30])
                return json.loads(cached)

        # API call
        url = f"{self.api_url}/paper/autocomplete"
        params = {"query": query, "limit": limit}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", [])

        # Cache for 1 hour per D-04
        if redis_client:
            await redis_client.setex(cache_key, 3600, json.dumps(result))
            logger.info("S2 autocomplete cached", query=query[:30])

        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search_authors(
        self,
        query: str,
        fields: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Search authors by name.

        Per D-05: Called from Author tab in frontend
        Per D-06: Return hIndex, citationCount, paperCount
        Per D-12: Cache for 24 hours

        Args:
            query: Author name query
            fields: Comma-separated fields (default: authorId,name,hIndex,citationCount,paperCount)
            limit: Max results (default 10)
            offset: Pagination offset
            redis_client: Optional Redis client

        Returns:
            Dict with 'data' list of authors
        """
        if not fields:
            fields = "authorId,name,hIndex,citationCount,paperCount"

        # Cache key per D-13
        cache_key = f"s2:author:search:{query}:{fields}:{limit}:{offset}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info("S2 author search cache hit", query=query[:30])
                return json.loads(cached)

        url = f"{self.api_url}/author/search"
        params = {"query": query, "fields": fields, "limit": limit, "offset": offset}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # Cache for 24 hours per D-12
        if redis_client:
            await redis_client.setex(cache_key, 86400, json.dumps(data))
            logger.info("S2 author search cached", query=query[:30])

        return data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_author_papers(
        self,
        author_id: str,
        fields: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Get papers by author ID.

        Per D-07: Pagination 10 per page
        Per D-12: Cache for 7 days (author papers change slowly)

        Args:
            author_id: Semantic Scholar author ID
            fields: Comma-separated fields (default: paperId,title,year,citationCount)
            limit: Max results (default 10 per D-07)
            offset: Pagination offset
            redis_client: Optional Redis client

        Returns:
            Dict with 'data' list of papers and optional 'next' offset
        """
        if not fields:
            fields = "paperId,title,year,citationCount"

        # Cache key per D-13
        cache_key = f"s2:author:{author_id}:papers:{fields}:{limit}:{offset}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info("S2 author papers cache hit", author_id=author_id)
                return json.loads(cached)

        url = f"{self.api_url}/author/{author_id}/papers"
        params = {"fields": fields, "limit": limit, "offset": offset}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # Cache for 7 days per D-12
        if redis_client:
            await redis_client.setex(cache_key, 604800, json.dumps(data))
            logger.info("S2 author papers cached", author_id=author_id)

        return data


# Singleton pattern (match existing services)
_s2_service: Optional[SemanticScholarService] = None


def get_semantic_scholar_service() -> SemanticScholarService:
    """Get or create SemanticScholarService singleton."""
    global _s2_service
    if _s2_service is None:
        _s2_service = SemanticScholarService()
    return _s2_service