"""Integration tests for PDF metadata enrichment.

Tests cover:
- Metadata enrichment triggered by missing title/authors
- Fuzzy title matching with 80% threshold
- Database updates with enriched metadata
- Skip when metadata complete
- Graceful failure handling

Per D-07, D-08, D-09.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from app.workers.pdf_worker import PDFProcessor, fuzzy_match_title
from app.core.semantic_scholar_service import SemanticScholarService


@pytest.fixture
def mock_s2_service():
    """Mock SemanticScholarService."""
    service = AsyncMock(spec=SemanticScholarService)
    return service


@pytest.fixture
def processor():
    """Create PDFProcessor instance."""
    return PDFProcessor()


class TestFuzzyMatchTitle:
    """Tests for fuzzy_match_title helper function."""

    def test_exact_match(self):
        """Test exact title match returns correct paper."""
        target = "Deep Learning for Natural Language Processing"
        candidates = [
            {"paperId": "1", "title": "Deep Learning for Natural Language Processing"},
            {"paperId": "2", "title": "Machine Learning Basics"},
        ]
        
        result = fuzzy_match_title(target, candidates, threshold=0.8)
        
        assert result is not None
        assert result["paperId"] == "1"

    def test_fuzzy_match_above_threshold(self):
        """Test fuzzy match with >80% similarity."""
        target = "Attention Is All You Need"
        candidates = [
            {"paperId": "1", "title": "Attention is All You Need"},  # Minor case difference
            {"paperId": "2", "title": "Attention Mechanisms in Neural Networks"},
        ]
        
        result = fuzzy_match_title(target, candidates, threshold=0.8)
        
        assert result is not None
        assert result["paperId"] == "1"

    def test_no_match_below_threshold(self):
        """Test returns None when similarity < 80%."""
        target = "Transformer Models in NLP"
        candidates = [
            {"paperId": "1", "title": "Recurrent Neural Networks for Text"},
            {"paperId": "2", "title": "Convolutional Neural Networks for Images"},
        ]
        
        result = fuzzy_match_title(target, candidates, threshold=0.8)
        
        assert result is None

    def test_best_match_selection(self):
        """Test selects best match from multiple candidates."""
        target = "BERT: Pre-training of Deep Bidirectional Transformers"
        candidates = [
            {"paperId": "1", "title": "GPT: Generative Pre-trained Transformer"},
            {"paperId": "2", "title": "BERT: Pre-training of Deep Bidirectional Transformers"},
            {"paperId": "3", "title": "RoBERTa: A Robustly Optimized BERT Approach"},
        ]
        
        result = fuzzy_match_title(target, candidates, threshold=0.8)
        
        assert result is not None
        assert result["paperId"] == "2"  # Exact match

    def test_empty_title_skipped(self):
        """Test candidates with empty titles are skipped."""
        target = "Some Paper Title"
        candidates = [
            {"paperId": "1", "title": ""},
            {"paperId": "2", "title": "Some Paper Title"},
        ]
        
        result = fuzzy_match_title(target, candidates, threshold=0.8)
        
        assert result is not None
        assert result["paperId"] == "2"


class TestEnrichMetadataIfNeeded:
    """Tests for enrich_metadata_if_needed method."""

    @pytest.mark.asyncio
    async def test_skip_when_metadata_complete(self, processor):
        """Test enrichment skipped when title and authors present."""
        # Mock database connection
        mock_conn = AsyncMock()
        
        # Call with complete metadata
        result = await processor.enrich_metadata_if_needed(
            conn=mock_conn,
            paper_id="test-paper-id",
            title="Existing Title",
            authors=["Author 1", "Author 2"]
        )
        
        assert result is False
        # Should not query S2
        mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_no_title(self, processor):
        """Test enrichment skipped when no title available."""
        mock_conn = AsyncMock()
        
        result = await processor.enrich_metadata_if_needed(
            conn=mock_conn,
            paper_id="test-paper-id",
            title=None,
            authors=[]
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_enrichment_with_missing_authors(self, processor, mock_s2_service):
        """Test enrichment triggered when authors missing."""
        mock_conn = AsyncMock()
        
        # Mock S2 search results
        search_results = {
            "data": [
                {
                    "paperId": "s2-id-123",
                    "title": "Matching Paper Title",
                    "year": 2023,
                    "authors": [{"name": "Author One"}, {"name": "Author Two"}],
                    "citationCount": 150,
                    "venue": "NeurIPS 2023"
                }
            ]
        }
        
        with patch('app.workers.pdf_worker.get_semantic_scholar_service', return_value=mock_s2_service):
            mock_s2_service.search_papers = AsyncMock(return_value=search_results)
            
            result = await processor.enrich_metadata_if_needed(
                conn=mock_conn,
                paper_id="test-paper-id",
                title="Matching Paper Title",
                authors=[]  # Missing authors
            )
            
            assert result is True
            # Verify database update was called
            mock_conn.execute.assert_called_once()
            
            # Check SQL update includes s2_paper_id
            call_args = mock_conn.execute.call_args
            sql = call_args[0][0]
            assert "s2_paper_id" in sql
            assert "citation_count" in sql
            assert "venue" in sql

    @pytest.mark.asyncio
    async def test_no_s2_results(self, processor, mock_s2_service):
        """Test handles no S2 search results gracefully."""
        mock_conn = AsyncMock()
        
        with patch('app.workers.pdf_worker.get_semantic_scholar_service', return_value=mock_s2_service):
            mock_s2_service.search_papers = AsyncMock(return_value={"data": []})
            
            result = await processor.enrich_metadata_if_needed(
                conn=mock_conn,
                paper_id="test-paper-id",
                title="Some Obscure Title",
                authors=[]
            )
            
            assert result is False
            # Should not update database
            mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_fuzzy_match_above_threshold(self, processor, mock_s2_service):
        """Test handles no match above 80% threshold."""
        mock_conn = AsyncMock()
        
        search_results = {
            "data": [
                {"paperId": "1", "title": "Completely Different Title"},
                {"paperId": "2", "title": "Another Unrelated Paper"},
            ]
        }
        
        with patch('app.workers.pdf_worker.get_semantic_scholar_service', return_value=mock_s2_service):
            mock_s2_service.search_papers = AsyncMock(return_value=search_results)
            
            result = await processor.enrich_metadata_if_needed(
                conn=mock_conn,
                paper_id="test-paper-id",
                title="Target Title Not In Results",
                authors=[]
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_s2_api_failure_doesnt_block(self, processor, mock_s2_service):
        """Test S2 API failure doesn't raise exception."""
        mock_conn = AsyncMock()
        
        with patch('app.workers.pdf_worker.get_semantic_scholar_service', return_value=mock_s2_service):
            # Simulate S2 API failure
            mock_s2_service.search_papers = AsyncMock(side_effect=Exception("S2 API Error"))
            
            # Should not raise exception
            result = await processor.enrich_metadata_if_needed(
                conn=mock_conn,
                paper_id="test-paper-id",
                title="Some Title",
                authors=[]
            )
            
            # Should return False (graceful degradation)
            assert result is False

    @pytest.mark.asyncio
    async def test_database_update_with_enriched_data(self, processor, mock_s2_service):
        """Test database updated with enriched metadata."""
        mock_conn = AsyncMock()
        
        search_results = {
            "data": [
                {
                    "paperId": "s2-paper-456",
                    "title": "Enriched Title",
                    "year": 2024,
                    "authors": [{"name": "Alice"}, {"name": "Bob"}],
                    "abstract": "Enriched abstract text",
                    "citationCount": 250,
                    "venue": "ICML 2024"
                }
            ]
        }
        
        with patch('app.workers.pdf_worker.get_semantic_scholar_service', return_value=mock_s2_service):
            mock_s2_service.search_papers = AsyncMock(return_value=search_results)
            
            result = await processor.enrich_metadata_if_needed(
                conn=mock_conn,
                paper_id="test-paper-id",
                title="Enriched Title",  # Matches
                authors=[]  # Missing
            )
            
            assert result is True
            
            # Verify UPDATE query parameters
            call_args = mock_conn.execute.call_args
            params = call_args[0]
            
            # Check paper_id
            assert params[1] == "test-paper-id"
            # Check s2_paper_id
            assert params[5] == "s2-paper-456"
            # Check citation_count
            assert params[6] == 250
            # Check venue
            assert params[7] == "ICML 2024"