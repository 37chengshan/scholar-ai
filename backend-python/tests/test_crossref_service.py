"""Tests for CrossRefService DOI resolution.

Tests cover:
- Valid DOI resolution (returns metadata)
- Invalid DOI handling (404 error)
- Redis caching (24h TTL)
- Cache hit behavior (no API call)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.core.crossref_service import CrossRefService


@pytest.mark.asyncio
async def test_resolve_doi_valid():
    """Test 1: resolve_doi returns SearchResult for valid DOI."""
    service = CrossRefService()

    # Mock httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "title": ["The DNA sequence of the human genome"],
            "author": [
                {"given": "J. Craig", "family": "Venter"},
                {"given": "Mark D.", "family": "Adams"}
            ],
            "published-print": {
                "date-parts": [[2001, 2, 15]]
            },
            "abstract": "The human genome is a complete set of human genetic information.",
            "DOI": "10.1038/nature12373",
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await service.resolve_doi("10.1038/nature12373", redis_client=None)

        assert result["id"] == "10.1038/nature12373"
        assert result["title"] == "The DNA sequence of the human genome"
        assert result["authors"] == ["J. Craig Adams", "Mark D. Adams"]
        assert result["year"] == 2001
        assert result["abstract"] == "The human genome is a complete set of human genetic information."
        assert result["source"] == "crossref"
        assert result["url"] == "https://doi.org/10.1038/nature12373"
        assert result["citationCount"] is None


@pytest.mark.asyncio
async def test_resolve_doi_error():
    """Test 2: resolve_doi returns 404 for invalid DOI."""
    service = CrossRefService()

    # Mock httpx.AsyncClient with 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with pytest.raises(HTTPException) as exc_info:
            await service.resolve_doi("10.1000/invalid", redis_client=None)

        assert exc_info.value.status_code == 404
        assert "DOI not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_crossref_caching():
    """Test 3: resolve_doi caches result in Redis with key 'search:doi:{doi}'."""
    service = CrossRefService()

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.setex = AsyncMock()

    # Mock httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "title": ["Test Paper"],
            "author": [{"given": "John", "family": "Doe"}],
            "published-print": {"date-parts": [[2020]]},
            "abstract": "Test abstract",
            "DOI": "10.1234/test",
        }
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await service.resolve_doi("10.1234/test", redis_client=mock_redis)

        # Verify cache key and TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "search:doi:10.1234/test"
        assert call_args[0][1] == 86400  # 24 hours

        # Verify cached data
        cached_data = json.loads(call_args[0][2])
        assert cached_data["id"] == "10.1234/test"
        assert cached_data["title"] == "Test Paper"


@pytest.mark.asyncio
async def test_crossref_cache_hit():
    """Test 4: resolve_doi returns cached result without API call on cache hit."""
    service = CrossRefService()

    # Mock Redis client with cached data
    cached_result = {
        "id": "10.5678/cached",
        "title": "Cached Paper",
        "authors": ["Jane Smith"],
        "year": 2019,
        "abstract": "Cached abstract",
        "source": "crossref",
        "url": "https://doi.org/10.5678/cached",
        "citationCount": None,
        "pdfUrl": None,
        "arxivId": None,
    }
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

    with patch("httpx.AsyncClient") as mock_client:
        # Should not call API
        result = await service.resolve_doi("10.5678/cached", redis_client=mock_redis)

        # Verify no API call was made
        mock_client.return_value.__aenter__.return_value.get.assert_not_called()

        # Verify returned cached result
        assert result["id"] == "10.5678/cached"
        assert result["title"] == "Cached Paper"
        assert result["year"] == 2019