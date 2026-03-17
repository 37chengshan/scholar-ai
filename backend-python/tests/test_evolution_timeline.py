"""Tests for the evolution timeline API.

Tests method evolution timeline generation including:
- Version extraction with LLM
- Timeline validation and sorting
- Pattern detection
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.api.compare import (
    EvolutionRequest,
    EvolutionTimeline,
    TimelineEntry,
    extract_versions_with_llm,
    validate_timeline_with_citations,
    detect_evolution_pattern,
    detect_evolution_timeline,
)


class TestEvolutionRequest:
    """Test EvolutionRequest model validation."""

    def test_valid_request_with_two_papers(self):
        """Test valid request with minimum 2 papers."""
        request = EvolutionRequest(
            paper_ids=["paper-1", "paper-2"],
            method_name="YOLO"
        )
        assert len(request.paper_ids) == 2
        assert request.method_name == "YOLO"

    def test_valid_request_with_twenty_papers(self):
        """Test valid request with maximum 20 papers."""
        request = EvolutionRequest(
            paper_ids=[f"paper-{i}" for i in range(20)],
            method_name="BERT"
        )
        assert len(request.paper_ids) == 20

    def test_invalid_request_with_one_paper(self):
        """Test that 1 paper raises validation error."""
        with pytest.raises(ValueError):
            EvolutionRequest(
                paper_ids=["paper-1"],
                method_name="YOLO"
            )

    def test_invalid_request_with_twenty_one_papers(self):
        """Test that 21 papers raises validation error."""
        with pytest.raises(ValueError):
            EvolutionRequest(
                paper_ids=[f"paper-{i}" for i in range(21)],
                method_name="YOLO"
            )

    def test_invalid_empty_method_name(self):
        """Test that empty method_name raises validation error."""
        with pytest.raises(ValueError):
            EvolutionRequest(
                paper_ids=["paper-1", "paper-2"],
                method_name=""
            )

    def test_method_name_too_long(self):
        """Test that method_name over 100 chars raises error."""
        with pytest.raises(ValueError):
            EvolutionRequest(
                paper_ids=["paper-1", "paper-2"],
                method_name="A" * 101
            )


class TestExtractVersionsWithLLM:
    """Test version extraction with LLM."""

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_extract_yolo_versions(self, mock_litellm):
        """Test version extraction for YOLO papers."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": '[{"paper_id": "1", "year": 2015, "version": "v1", "key_changes": "First version"}, {"paper_id": "2", "year": 2016, "version": "v2", "key_changes": "9000 classes"}, {"paper_id": "3", "year": 2018, "version": "v3", "key_changes": "Incremental improvements"}]'
                }
            }]
        }
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        papers = [
            {"id": "1", "title": "YOLO: You Only Look Once", "year": 2015, "abstract": "Real-time detection"},
            {"id": "2", "title": "YOLO9000: Better, Faster, Stronger", "year": 2016, "abstract": "Improved version"},
            {"id": "3", "title": "YOLOv3: An Incremental Improvement", "year": 2018, "abstract": "Even better"},
        ]

        result = await extract_versions_with_llm(papers, "YOLO")

        assert len(result) == 3
        assert result[0]['version'] == 'v1'
        assert result[1]['version'] == 'v2'
        assert result[2]['version'] == 'v3'
        mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_extract_bert_variants(self, mock_litellm):
        """Test version extraction for BERT variants."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": '[{"paper_id": "1", "year": 2018, "version": "base", "key_changes": "Base model"}, {"paper_id": "2", "year": 2019, "version": "large", "key_changes": "Larger model"}]'
                }
            }]
        }
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        papers = [
            {"id": "1", "title": "BERT: Pre-training", "year": 2018, "abstract": "Base"},
            {"id": "2", "title": "BERT-large", "year": 2019, "abstract": "Large"},
        ]

        result = await extract_versions_with_llm(papers, "BERT")

        assert len(result) == 2
        assert result[0]['version'] == 'base'
        mock_litellm.acompletion.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_extract_handles_wrapped_response(self, mock_litellm):
        """Test extraction handles object-wrapped array response."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": '{"versions": [{"paper_id": "1", "year": 2020, "version": "v1", "key_changes": "Test"}]}'
                }
            }]
        }
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        papers = [
            {"id": "1", "title": "Test Paper", "year": 2020, "abstract": "Test"},
        ]

        result = await extract_versions_with_llm(papers, "Test")

        assert len(result) == 1
        assert result[0]['version'] == 'v1'

    @pytest.mark.asyncio
    @patch('app.api.compare.litellm')
    async def test_extract_handles_llm_error(self, mock_litellm):
        """Test extraction handles LLM errors."""
        mock_litellm.acompletion = AsyncMock(side_effect=Exception("LLM error"))

        papers = [
            {"id": "1", "title": "Test Paper", "year": 2020, "abstract": "Test"},
        ]

        with pytest.raises(HTTPException) as exc_info:
            await extract_versions_with_llm(papers, "Test")

        assert exc_info.value.status_code == 500
        assert "Failed to extract version information" in exc_info.value.detail


class TestValidateTimelineWithCitations:
    """Test timeline validation and sorting."""

    def test_timeline_sorted_by_year(self):
        """Test timeline is sorted by year ascending."""
        unsorted = [
            {"year": 2018, "paper_id": "3", "version": "v3"},
            {"year": 2015, "paper_id": "1", "version": "v1"},
            {"year": 2016, "paper_id": "2", "version": "v2"},
        ]

        result = validate_timeline_with_citations(unsorted, ["1", "2", "3"])

        years = [entry['year'] for entry in result]
        assert years == [2015, 2016, 2018]

    def test_timeline_adds_validation_metadata(self):
        """Test validation adds metadata to entries."""
        timeline = [
            {"year": 2015, "paper_id": "1", "version": "v1"},
        ]

        result = validate_timeline_with_citations(timeline, ["1"])

        assert result[0]['validated'] is True
        assert result[0]['temporal_consistency'] == 'checked'

    def test_timeline_handles_missing_years(self):
        """Test timeline handles entries without years."""
        timeline = [
            {"year": 2016, "paper_id": "2", "version": "v2"},
            {"paper_id": "3", "version": "v3"},  # No year
            {"year": 2015, "paper_id": "1", "version": "v1"},
        ]

        result = validate_timeline_with_citations(timeline, ["1", "2", "3"])

        # Entries without year should be at the end (sorted by 9999)
        assert result[-1]['paper_id'] == '3'

    def test_empty_timeline(self):
        """Test empty timeline returns empty list."""
        result = validate_timeline_with_citations([], [])
        assert result == []


class TestDetectEvolutionPattern:
    """Test evolution pattern detection."""

    def test_pattern_performance_improvements(self):
        """Test pattern detection for performance-focused evolution."""
        timeline = [
            {"year": 2015, "version": "v1", "key_changes": "Basic accuracy improvements"},
            {"year": 2016, "version": "v2", "key_changes": "Better performance and higher accuracy"},
            {"year": 2018, "version": "v3", "key_changes": "State-of-the-art accuracy"},
        ]

        pattern = detect_evolution_pattern(timeline)

        assert "performance" in pattern.lower() or "accuracy" in pattern.lower()

    def test_pattern_efficiency_optimizations(self):
        """Test pattern detection for efficiency-focused evolution."""
        timeline = [
            {"year": 2015, "version": "v1", "key_changes": "Standard model"},
            {"year": 2016, "version": "v2", "key_changes": "Faster inference, more efficient"},
            {"year": 2018, "version": "v3", "key_changes": "Lightweight version for mobile"},
        ]

        pattern = detect_evolution_pattern(timeline)

        assert "efficiency" in pattern.lower() or any(term in pattern.lower() for term in ['speed', 'optimization'])

    def test_pattern_scaling_up(self):
        """Test pattern detection for scaling evolution."""
        timeline = [
            {"year": 2018, "version": "base", "key_changes": "Standard BERT"},
            {"year": 2019, "version": "large", "key_changes": "Bigger model, more layers"},
            {"year": 2020, "version": "xlarge", "key_changes": "Deep learning at scale"},
        ]

        pattern = detect_evolution_pattern(timeline)

        assert "scale" in pattern.lower() or "capacity" in pattern.lower()

    def test_pattern_rapid_iteration(self):
        """Test pattern detection for rapid iteration."""
        timeline = [
            {"year": 2023, "version": "v1", "key_changes": "First release"},
            {"year": 2023, "version": "v2", "key_changes": "Quick fix"},
        ]

        pattern = detect_evolution_pattern(timeline)

        assert "rapid" in pattern.lower() or "iteration" in pattern.lower()

    def test_pattern_long_development(self):
        """Test pattern detection for long development span."""
        timeline = [
            {"year": 2010, "version": "v1", "key_changes": "Initial"},
            {"year": 2020, "version": "v2", "key_changes": "Ten years later"},
        ]

        pattern = detect_evolution_pattern(timeline)

        assert "10 years" in pattern or "developed over" in pattern

    def test_empty_timeline(self):
        """Test empty timeline returns appropriate message."""
        pattern = detect_evolution_pattern([])
        assert pattern == "No evolution data available"

    def test_single_entry_timeline(self):
        """Test single entry returns insufficient data message."""
        timeline = [
            {"year": 2020, "version": "v1", "key_changes": "Only version"},
        ]

        pattern = detect_evolution_pattern(timeline)
        assert "Insufficient" in pattern

    def test_unknown_versions(self):
        """Test pattern with unknown versions."""
        timeline = [
            {"year": 2015, "version": "unknown", "key_changes": "First"},
            {"year": 2016, "version": "unknown", "key_changes": "Second"},
        ]

        pattern = detect_evolution_pattern(timeline)
        # Should not mention version count since all are unknown
        assert "distinct versions" not in pattern.lower()


class TestEvolutionTimeline:
    """Test EvolutionTimeline model."""

    def test_timeline_structure(self):
        """Test timeline has all required fields."""
        timeline = EvolutionTimeline(
            method="YOLO",
            paper_count=3,
            timeline=[
                TimelineEntry(
                    year=2015,
                    version="v1",
                    paper_id="paper-1",
                    paper_title="YOLO v1",
                    key_changes="First version"
                ),
                TimelineEntry(
                    year=2016,
                    version="v2",
                    paper_id="paper-2",
                    paper_title="YOLO v2",
                    key_changes="Better, faster"
                ),
            ],
            summary="Method evolved through rapid iteration"
        )

        assert timeline.method == "YOLO"
        assert timeline.paper_count == 3
        assert len(timeline.timeline) == 2
        assert timeline.timeline[0].year == 2015
        assert timeline.timeline[1].version == "v2"

    def test_timeline_entry_structure(self):
        """Test timeline entry has all required fields."""
        entry = TimelineEntry(
            year=2020,
            version="v1",
            paper_id="paper-1",
            paper_title="Test Paper",
            key_changes="Initial release"
        )

        assert entry.year == 2020
        assert entry.version == "v1"
        assert entry.paper_id == "paper-1"
        assert entry.paper_title == "Test Paper"
        assert entry.key_changes == "Initial release"


class TestDetectEvolutionTimelineEndpoint:
    """Test detect_evolution_timeline endpoint."""

    @pytest.mark.asyncio
    @patch('app.api.compare.get_db_connection')
    @patch('app.api.compare.extract_versions_with_llm')
    async def test_endpoint_success(self, mock_extract, mock_get_conn):
        """Test successful timeline generation."""
        # Mock database
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "1", "title": "YOLO v1", "authors": ["A"], "year": 2015, "abstract": "Test"},
            {"id": "2", "title": "YOLO v2", "authors": ["B"], "year": 2016, "abstract": "Test"},
        ])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_conn.return_value = mock_context

        # Mock LLM extraction
        mock_extract.return_value = [
            {"paper_id": "1", "year": 2015, "version": "v1", "key_changes": "First"},
            {"paper_id": "2", "year": 2016, "version": "v2", "key_changes": "Second"},
        ]

        request = EvolutionRequest(
            paper_ids=["1", "2"],
            method_name="YOLO"
        )

        result = await detect_evolution_timeline(request, {"user_id": "user-1"})

        assert result.method == "YOLO"
        assert result.paper_count == 2
        assert len(result.timeline) == 2
        assert result.timeline[0].year == 2015
        assert result.timeline[1].year == 2016
        assert result.summary is not None

    @pytest.mark.asyncio
    @patch('app.api.compare.get_db_connection')
    async def test_endpoint_missing_papers(self, mock_get_conn):
        """Test endpoint with missing papers returns 404."""
        # Mock database - return only 1 paper when 2 requested
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "1", "title": "YOLO v1", "authors": ["A"], "year": 2015, "abstract": "Test"},
        ])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_conn.return_value = mock_context

        request = EvolutionRequest(
            paper_ids=["1", "2"],
            method_name="YOLO"
        )

        with pytest.raises(HTTPException) as exc_info:
            await detect_evolution_timeline(request, {"user_id": "user-1"})

        assert exc_info.value.status_code == 404
        assert "2" in str(exc_info.value.detail)
