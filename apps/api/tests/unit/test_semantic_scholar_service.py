"""Unit tests for SemanticScholarService.

Tests cover:
- Batch operations (max 1000 IDs)
- Citation network endpoints
- Paper details retrieval
- Retry behavior on rate limits
- Cache key generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json

from app.core.semantic_scholar_service import SemanticScholarService, get_semantic_scholar_service


@pytest.fixture
def s2_service():
    """Create SemanticScholarService instance."""
    return SemanticScholarService()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


class TestBatchGetPapers:
    """Tests for batch_get_papers method."""

    @pytest.mark.asyncio
    async def test_batch_get_papers(self, s2_service, mock_redis):
        """Test batch_get_papers returns list of papers."""
        paper_ids = ["id1", "id2"]
        
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"paperId": "id1", "title": "Paper 1"},
            {"paperId": "id2", "title": "Paper 2"}
        ]
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await s2_service.batch_get_papers(paper_ids, redis_client=mock_redis)
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["paperId"] == "id1"

    @pytest.mark.asyncio
    async def test_batch_get_papers_limit_1000(self, s2_service, mock_redis):
        """Test batch truncates to 1000 IDs if exceeded."""
        paper_ids = [f"id{i}" for i in range(1500)]  # 1500 IDs
        
        mock_response = MagicMock()
        mock_response.json.return_value = [{"paperId": f"id{i}"} for i in range(1000)]
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            
            # Should log warning and truncate
            result = await s2_service.batch_get_papers(paper_ids, redis_client=mock_redis)
            
            # Verify only first 1000 were requested
            call_args = mock_client.return_value.post.call_args
            assert len(call_args[1]["json"]["ids"]) == 1000

    @pytest.mark.asyncio
    async def test_batch_get_papers_cache_hit(self, s2_service):
        """Test batch returns cached data when available."""
        paper_ids = ["id1", "id2"]
        cached_data = [{"paperId": "id1", "title": "Cached Paper 1"}]
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        
        result = await s2_service.batch_get_papers(paper_ids, redis_client=mock_redis)
        
        assert result == cached_data
        # Should NOT call API
        mock_redis.get.assert_called_once()


class TestGetCitations:
    """Tests for get_citations method."""

    @pytest.mark.asyncio
    async def test_get_citations(self, s2_service, mock_redis):
        """Test get_citations returns list of citing papers."""
        paper_id = "test-paper-id"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "citing1", "title": "Citing Paper 1"},
                {"paperId": "citing2", "title": "Citing Paper 2"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await s2_service.get_citations(paper_id, redis_client=mock_redis)
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["paperId"] == "citing1"

    @pytest.mark.asyncio
    async def test_get_citations_default_limit_1000(self, s2_service):
        """Test citations default limit is 1000."""
        paper_id = "test-paper-id"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            await s2_service.get_citations(paper_id)
            
            # Check limit parameter
            call_args = mock_client.return_value.get.call_args
            assert call_args[1]["params"]["limit"] == 1000


class TestGetReferences:
    """Tests for get_references method."""

    @pytest.mark.asyncio
    async def test_get_references(self, s2_service, mock_redis):
        """Test get_references returns list of referenced papers."""
        paper_id = "test-paper-id"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "ref1", "title": "Reference Paper 1"},
                {"paperId": "ref2", "title": "Reference Paper 2"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await s2_service.get_references(paper_id, redis_client=mock_redis)
            
            assert isinstance(result, list)
            assert len(result) == 2


class TestGetPaperDetails:
    """Tests for get_paper_details method."""

    @pytest.mark.asyncio
    async def test_get_paper_details(self, s2_service, mock_redis):
        """Test get_paper_details returns paper dict."""
        paper_id = "test-paper-id"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "paperId": paper_id,
            "title": "Test Paper",
            "year": 2023,
            "authors": [{"name": "Author 1"}]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await s2_service.get_paper_details(paper_id, redis_client=mock_redis)
            
            assert isinstance(result, dict)
            assert result["paperId"] == paper_id
            assert result["title"] == "Test Paper"

    @pytest.mark.asyncio
    async def test_get_paper_details_cache_hit(self, s2_service):
        """Test paper details returns cached data when available."""
        paper_id = "test-paper-id"
        cached_data = {"paperId": paper_id, "title": "Cached Paper"}
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        
        result = await s2_service.get_paper_details(paper_id, redis_client=mock_redis)
        
        assert result == cached_data


class TestRetryBehavior:
    """Tests for retry behavior on rate limits."""

    @pytest.mark.asyncio
    async def test_retry_on_429(self, s2_service):
        """Test retry on rate limit error (429)."""
        paper_id = "test-paper-id"
        
        # First call: 429 error
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=MagicMock(), response=error_response
        )
        
        # Second call: success
        success_response = MagicMock()
        success_response.json.return_value = {"paperId": paper_id}
        success_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_post = AsyncMock()
            mock_post.side_effect = [error_response, success_response]
            mock_client.return_value.post = mock_post
            
            # Should retry and succeed
            result = await s2_service.batch_get_papers([paper_id])
            
            # Should have made 2 attempts
            assert mock_post.call_count == 2


class TestSearchPapers:
    """Tests for search_papers method."""

    @pytest.mark.asyncio
    async def test_search_papers(self, s2_service, mock_redis):
        """Test search_papers returns search results."""
        query = "machine learning"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "id1", "title": "ML Paper 1"},
                {"paperId": "id2", "title": "ML Paper 2"}
            ],
            "total": 2
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await s2_service.search_papers(query, redis_client=mock_redis)
            
            assert isinstance(result, dict)
            assert "data" in result
            assert len(result["data"]) == 2
            assert result["data"][0]["paperId"] == "id1"

    @pytest.mark.asyncio
    async def test_search_papers_with_fields(self, s2_service, mock_redis):
        """Test search_papers with custom fields."""
        query = "deep learning"
        fields = "paperId,title,year,authors"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"paperId": "id1"}]}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            await s2_service.search_papers(query, fields=fields, redis_client=mock_redis)
            
            # Check fields parameter
            call_args = mock_client.return_value.get.call_args
            assert call_args[1]["params"]["fields"] == fields

    @pytest.mark.asyncio
    async def test_search_papers_with_limit(self, s2_service):
        """Test search_papers with limit parameter."""
        query = "neural networks"
        limit = 5
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            await s2_service.search_papers(query, limit=limit)
            
            # Check limit parameter
            call_args = mock_client.return_value.get.call_args
            assert call_args[1]["params"]["limit"] == limit

    @pytest.mark.asyncio
    async def test_search_papers_cache_hit(self, s2_service):
        """Test search_papers returns cached results."""
        query = "transformer models"
        cached_data = {"data": [{"paperId": "cached-id"}], "total": 1}
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        
        result = await s2_service.search_papers(query, redis_client=mock_redis)
        
        assert result == cached_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_papers_cache_key_format(self, s2_service):
        """Test search_papers cache key follows D-11 format."""
        query = "attention mechanism"
        fields = "paperId,title"
        limit = 10
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            await s2_service.search_papers(query, fields=fields, limit=limit, redis_client=mock_redis)
            
            # Check cache key format: s2:search:{query}:{fields}:{limit}
            cache_key = mock_redis.setex.call_args[0][0]
            assert cache_key.startswith("s2:search:")
            assert query in cache_key
            assert fields in cache_key
            assert str(limit) in cache_key


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_semantic_scholar_service_singleton(self):
        """Test get_semantic_scholar_service returns singleton."""
        service1 = get_semantic_scholar_service()
        service2 = get_semantic_scholar_service()
        
        assert service1 is service2
        assert isinstance(service1, SemanticScholarService)


class TestAutocompletePapers:
    """Tests for autocomplete_papers method (Phase 23)."""

    @pytest.mark.asyncio
    async def test_autocomplete_papers(self, s2_service, mock_redis):
        """Test autocomplete_papers returns list of papers."""
        query = "attention"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "id1", "title": "Attention Is All You Need", "year": 2017},
                {"paperId": "id2", "title": "Attention Mechanisms in NLP", "year": 2019}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await s2_service.autocomplete_papers(query, redis_client=mock_redis)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["paperId"] == "id1"

    @pytest.mark.asyncio
    async def test_autocomplete_papers_cache_hit(self, s2_service):
        """Test autocomplete returns cached data when available."""
        query = "transformer"
        cached_data = [{"paperId": "cached-id", "title": "Cached Paper"}]

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await s2_service.autocomplete_papers(query, redis_client=mock_redis)

        assert result == cached_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_autocomplete_papers_default_limit_5(self, s2_service):
        """Test autocomplete default limit is 5 per D-03."""
        query = "machine learning"

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.autocomplete_papers(query)

            call_args = mock_client.return_value.get.call_args
            assert call_args[1]["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_autocomplete_papers_cache_ttl_1h(self, s2_service):
        """Test autocomplete cache TTL is 3600s (1 hour) per D-04."""
        query = "deep learning"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"paperId": "id1"}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.autocomplete_papers(query, redis_client=mock_redis)

            # Check TTL is 3600 (1 hour)
            ttl = mock_redis.setex.call_args[0][1]
            assert ttl == 3600


class TestSearchAuthors:
    """Tests for search_authors method (Phase 23)."""

    @pytest.mark.asyncio
    async def test_search_authors(self, s2_service, mock_redis):
        """Test search_authors returns author list with hIndex."""
        query = "Geoffrey Hinton"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"authorId": "id1", "name": "Geoffrey Hinton", "hIndex": 89, "citationCount": 35526, "paperCount": 300}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await s2_service.search_authors(query, redis_client=mock_redis)

            assert isinstance(result, dict)
            assert "data" in result
            assert result["data"][0]["hIndex"] == 89

    @pytest.mark.asyncio
    async def test_search_authors_cache_hit(self, s2_service):
        """Test author search returns cached data."""
        query = "Yann LeCun"
        cached_data = {"data": [{"authorId": "cached-id", "name": "Yann LeCun"}]}

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await s2_service.search_authors(query, redis_client=mock_redis)

        assert result == cached_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_authors_default_fields(self, s2_service):
        """Test author search default fields include hIndex, citationCount, paperCount per D-06."""
        query = "Yoshua Bengio"

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.search_authors(query)

            call_args = mock_client.return_value.get.call_args
            fields = call_args[1]["params"]["fields"]
            assert "hIndex" in fields
            assert "citationCount" in fields
            assert "paperCount" in fields

    @pytest.mark.asyncio
    async def test_search_authors_cache_ttl_24h(self, s2_service):
        """Test author search cache TTL is 86400s (24 hours) per D-12."""
        query = "Andrew Ng"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.search_authors(query, redis_client=mock_redis)

            ttl = mock_redis.setex.call_args[0][1]
            assert ttl == 86400


class TestGetAuthorPapers:
    """Tests for get_author_papers method (Phase 23)."""

    @pytest.mark.asyncio
    async def test_get_author_papers(self, s2_service, mock_redis):
        """Test get_author_papers returns paginated paper list."""
        author_id = "1692545"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "paper1", "title": "Deep Learning", "year": 2015, "citationCount": 10000},
                {"paperId": "paper2", "title": "Paper 2", "year": 2018, "citationCount": 500}
            ],
            "next": 10
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await s2_service.get_author_papers(author_id, redis_client=mock_redis)

            assert isinstance(result, dict)
            assert "data" in result
            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_author_papers_pagination(self, s2_service, mock_redis):
        """Test author papers pagination with limit and offset."""
        author_id = "1692545"
        limit = 10
        offset = 20

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "next": 30}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.get_author_papers(author_id, limit=limit, offset=offset, redis_client=mock_redis)

            call_args = mock_client.return_value.get.call_args
            assert call_args[1]["params"]["limit"] == limit
            assert call_args[1]["params"]["offset"] == offset

    @pytest.mark.asyncio
    async def test_get_author_papers_cache_hit(self, s2_service):
        """Test author papers returns cached data."""
        author_id = "1692545"
        cached_data = {"data": [{"paperId": "cached-paper"}]}

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await s2_service.get_author_papers(author_id, redis_client=mock_redis)

        assert result == cached_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_author_papers_cache_ttl_7d(self, s2_service):
        """Test author papers cache TTL is 604800s (7 days) per D-12."""
        author_id = "1692545"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, '__aenter__') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            await s2_service.get_author_papers(author_id, redis_client=mock_redis)

            ttl = mock_redis.setex.call_args[0][1]
            assert ttl == 604800