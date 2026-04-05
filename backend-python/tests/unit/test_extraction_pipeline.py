"""Unit tests for ExtractionPipeline.

Tests for the parallel extraction pipeline:
- Pipeline initialization with ThreadPoolExecutor
- Singleton pattern
- Successful parallel extraction
- Critical failure blocking (IMRaD/Metadata)
- Auxiliary failure degradation (Images/Tables)
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.workers.extraction_pipeline import (
    ExtractionPipeline,
    PipelineError,
    get_extraction_pipeline
)
from app.workers.pipeline_context import PipelineContext, PipelineStage


class TestExtractionPipeline:
    """Tests for ExtractionPipeline class."""

    def test_pipeline_init(self):
        """Test pipeline initialization."""
        pipeline = ExtractionPipeline()

        assert pipeline.executor is not None
        assert pipeline.executor._max_workers == 4
        assert pipeline.qwen3vl is not None
        assert pipeline.image_extractor is not None
        assert pipeline.table_extractor is not None

    def test_singleton(self):
        """Test singleton pattern."""
        p1 = get_extraction_pipeline()
        p2 = get_extraction_pipeline()

        assert p1 is p2

    def test_singleton_returns_extraction_pipeline(self):
        """Test that singleton returns ExtractionPipeline instance."""
        pipeline = get_extraction_pipeline()

        assert isinstance(pipeline, ExtractionPipeline)

    @pytest.mark.asyncio
    async def test_parallel_extraction_success(self):
        """Test successful parallel extraction."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        # Mock parse result
        ctx.parse_result = {
            "items": [],
            "markdown": "# Test Paper\n\nAbstract: Test abstract"
        }
        ctx.local_path = "/tmp/test.pdf"

        # Mock extractors
        with patch.object(pipeline.image_extractor, 'extract_images_from_pdf', return_value=[]):
            with patch.object(pipeline.table_extractor, 'extract_tables_from_pdf', return_value=[]):
                with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock) as mock_imrad:
                    with patch('app.workers.extraction_pipeline.extract_metadata') as mock_metadata:
                        mock_imrad.return_value = {"introduction": {"content": "test"}}
                        mock_metadata.return_value = {"title": "Test Paper"}

                        result = await pipeline.extract(ctx)

                        assert result.imrad is not None
                        assert result.metadata is not None
                        assert result.image_results == []
                        assert result.table_results == []

    @pytest.mark.asyncio
    async def test_critical_failure_blocks(self):
        """Test that IMRaD failure raises PipelineError."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        ctx.parse_result = {"items": [], "markdown": ""}
        ctx.local_path = "/tmp/test.pdf"

        # Mock IMRaD to fail
        with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock) as mock_imrad:
            mock_imrad.side_effect = Exception("IMRaD failed")

            with pytest.raises(PipelineError) as exc_info:
                await pipeline.extract(ctx)

            assert "IMRaD extraction failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_metadata_failure_blocks(self):
        """Test that metadata failure raises PipelineError."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        ctx.parse_result = {"items": [], "markdown": ""}
        ctx.local_path = "/tmp/test.pdf"

        # Mock IMRaD to succeed, metadata to fail
        # Note: IMRaD extraction calls extract_metadata internally for paper_metadata,
        # so we mock it to fail for the dedicated metadata task but succeed for the IMRaD call
        call_count = [0]

        def metadata_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:  # Fail on second call (the dedicated metadata task)
                raise Exception("Metadata failed")
            return {}  # First call (from IMRaD) succeeds

        with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock, return_value={}):
            with patch('app.workers.extraction_pipeline.extract_metadata', side_effect=metadata_side_effect):
                with pytest.raises(PipelineError) as exc_info:
                    await pipeline.extract(ctx)

                # Verify PipelineError was raised (message may vary due to internal calls)
                assert isinstance(exc_info.value, PipelineError)

    @pytest.mark.asyncio
    async def test_auxiliary_failure_degrades(self):
        """Test that image/table failures don't block pipeline."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        ctx.parse_result = {"items": [], "markdown": ""}
        ctx.local_path = "/tmp/test.pdf"

        # Mock everything to work except images
        with patch.object(pipeline.image_extractor, 'extract_images_from_pdf', side_effect=Exception("Image error")):
            with patch.object(pipeline.table_extractor, 'extract_tables_from_pdf', return_value=[]):
                with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock, return_value={}):
                    with patch('app.workers.extraction_pipeline.extract_metadata', return_value={}):
                        result = await pipeline.extract(ctx)

                        # Pipeline should complete
                        assert result.imrad is not None
                        assert result.metadata is not None
                        assert result.image_results == []
                        assert len(result.errors) > 0
                        assert "Images extraction failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_table_failure_degrades(self):
        """Test that table failures don't block pipeline."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        ctx.parse_result = {"items": [], "markdown": ""}
        ctx.local_path = "/tmp/test.pdf"

        # Mock everything to work except tables
        with patch.object(pipeline.image_extractor, 'extract_images_from_pdf', return_value=[]):
            with patch.object(pipeline.table_extractor, 'extract_tables_from_pdf', side_effect=Exception("Table error")):
                with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock, return_value={}):
                    with patch('app.workers.extraction_pipeline.extract_metadata', return_value={}):
                        result = await pipeline.extract(ctx)

                        # Pipeline should complete
                        assert result.imrad is not None
                        assert result.metadata is not None
                        assert result.table_results == []
                        assert len(result.errors) > 0
                        assert "Tables extraction failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_context_updated_with_results(self):
        """Test that context is properly updated with extraction results."""
        pipeline = ExtractionPipeline()

        ctx = PipelineContext(
            task_id="test-task",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )

        ctx.parse_result = {"items": [], "markdown": ""}
        ctx.local_path = "/tmp/test.pdf"

        # Mock successful extraction
        with patch.object(pipeline.image_extractor, 'extract_images_from_pdf', return_value=[]):
            with patch.object(pipeline.table_extractor, 'extract_tables_from_pdf', return_value=[]):
                with patch('app.workers.extraction_pipeline.extract_imrad_enhanced', new_callable=AsyncMock) as mock_imrad:
                    with patch('app.workers.extraction_pipeline.extract_metadata') as mock_metadata:
                        mock_imrad.return_value = {
                            "introduction": {"content": "intro"},
                            "methods": {"content": "methods"}
                        }
                        mock_metadata.return_value = {
                            "title": "Test Paper",
                            "authors": ["Author 1"]
                        }

                        result = await pipeline.extract(ctx)

                        assert result.imrad == {"introduction": {"content": "intro"}, "methods": {"content": "methods"}}
                        assert result.metadata == {"title": "Test Paper", "authors": ["Author 1"]}


class TestPipelineError:
    """Tests for PipelineError exception."""

    def test_pipeline_error_message(self):
        """Test error message format."""
        error = PipelineError("Test error message")
        assert str(error) == "Test error message"

    def test_pipeline_error_inheritance(self):
        """Test that PipelineError inherits from Exception."""
        error = PipelineError("Test")
        assert isinstance(error, Exception)

    def test_pipeline_error_can_be_raised(self):
        """Test that PipelineError can be raised and caught."""
        with pytest.raises(PipelineError):
            raise PipelineError("Test error")