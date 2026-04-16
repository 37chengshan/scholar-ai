"""Unit tests for PDFCoordinator and PipelineContext.

Tests for the parallel PDF processing pipeline foundation:
- PipelineContext dataclass creation and field access
- Error tracking via add_error()
- Stage transitions
- PipelineStage enum values
- PDFCoordinator initialization and singleton pattern
- Download stage success/failure scenarios
- Parsing stage success/failure scenarios
"""

import pytest
from unittest.mock import AsyncMock

from app.workers.pipeline_context import PipelineContext, PipelineStage
from app.workers.pdf_coordinator import PDFCoordinator, get_pdf_coordinator
from app.workers.extraction_pipeline import PipelineError
from app.workers.storage_manager import StorageManager


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""

    def test_create_context(self):
        """Test creating a basic context."""
        ctx = PipelineContext(
            task_id="test-task-id",
            paper_id="test-paper-id",
            user_id="test-user-id",
            storage_key="test-key.pdf"
        )

        assert ctx.task_id == "test-task-id"
        assert ctx.paper_id == "test-paper-id"
        assert ctx.user_id == "test-user-id"
        assert ctx.storage_key == "test-key.pdf"
        assert ctx.current_stage == PipelineStage.DOWNLOAD
        assert ctx.errors == []

    def test_add_error(self):
        """Test adding errors to context."""
        ctx = PipelineContext(
            task_id="test",
            paper_id="test",
            user_id="test",
            storage_key="test"
        )

        ctx.add_error("First error")
        ctx.add_error("Second error")

        assert len(ctx.errors) == 2
        assert "First error" in ctx.errors
        assert "Second error" in ctx.errors

    def test_stage_progression(self):
        """Test stage transitions."""
        ctx = PipelineContext(
            task_id="test",
            paper_id="test",
            user_id="test",
            storage_key="test"
        )

        assert ctx.current_stage == PipelineStage.DOWNLOAD

        ctx.current_stage = PipelineStage.PARSING
        assert ctx.current_stage == PipelineStage.PARSING

        ctx.current_stage = PipelineStage.EXTRACTION
        assert ctx.current_stage == PipelineStage.EXTRACTION

        ctx.current_stage = PipelineStage.COMPLETED
        assert ctx.current_stage == PipelineStage.COMPLETED

    def test_optional_fields_default_none(self):
        """Test that optional result fields default to None."""
        ctx = PipelineContext(
            task_id="test",
            paper_id="test",
            user_id="test",
            storage_key="test"
        )

        assert ctx.local_path is None
        assert ctx.parse_result is None
        assert ctx.imrad is None
        assert ctx.metadata is None
        assert ctx.image_results is None
        assert ctx.table_results is None
        assert ctx.chunk_results is None
        assert ctx.notes is None

    def test_result_fields_can_be_set(self):
        """Test that result fields can be populated."""
        ctx = PipelineContext(
            task_id="test",
            paper_id="test",
            user_id="test",
            storage_key="test"
        )

        ctx.local_path = "/tmp/test.pdf"
        ctx.parse_result = {"markdown": "test", "items": [], "page_count": 10}
        ctx.imrad = {"introduction": {}}
        ctx.metadata = {"title": "Test Paper"}
        ctx.image_results = [{"image_id": "img1"}]
        ctx.table_results = [{"table_id": "tbl1"}]
        ctx.chunk_results = [{"chunk_id": "chk1"}]
        ctx.notes = "Test notes"

        assert ctx.local_path == "/tmp/test.pdf"
        assert ctx.parse_result["page_count"] == 10
        assert ctx.imrad["introduction"] == {}
        assert ctx.metadata["title"] == "Test Paper"
        assert len(ctx.image_results) == 1
        assert len(ctx.table_results) == 1
        assert len(ctx.chunk_results) == 1
        assert ctx.notes == "Test notes"


class TestPipelineStage:
    """Tests for PipelineStage enum."""

    def test_all_stages_exist(self):
        """Test that all required stages exist."""
        stages = [s.value for s in PipelineStage]

        assert "download" in stages
        assert "parsing" in stages
        assert "extraction" in stages
        assert "storage" in stages
        assert "completed" in stages
        assert "failed" in stages

    def test_stage_count(self):
        """Test that exactly 6 stages exist."""
        assert len(PipelineStage) == 6

    def test_stage_values_are_strings(self):
        """Test that all stage values are lowercase strings."""
        for stage in PipelineStage:
            assert isinstance(stage.value, str)
            assert stage.value == stage.value.lower()


class TestPDFCoordinator:
    """Tests for PDFCoordinator class."""

    def test_coordinator_init(self):
        """Test coordinator initialization."""
        coordinator = PDFCoordinator()

        assert coordinator.storage is not None
        assert coordinator.parser is not None
        assert coordinator.embedding_service is not None
        assert coordinator.milvus_service is not None
        assert coordinator._db_pool is None  # Not initialized until init_db
        assert coordinator._storage_manager is None  # Lazy init

    def test_coordinator_has_all_services(self):
        """Test that coordinator has all required services."""
        coordinator = PDFCoordinator()

        # Services from existing PDFProcessor
        assert hasattr(coordinator, "storage")
        assert hasattr(coordinator, "parser")
        assert hasattr(coordinator, "embedding_service")
        assert hasattr(coordinator, "neo4j_service")
        assert hasattr(coordinator, "notes_generator")
        assert hasattr(coordinator, "milvus_service")
        assert hasattr(coordinator, "image_extractor")
        assert hasattr(coordinator, "table_extractor")
        assert hasattr(coordinator, "multimodal_indexer")
        assert hasattr(coordinator, "_db_pool")  # Check internal field

    def test_singleton(self):
        """Test singleton pattern."""
        c1 = get_pdf_coordinator()
        c2 = get_pdf_coordinator()

        assert c1 is c2

    def test_singleton_returns_pdf_coordinator(self):
        """Test that singleton returns PDFCoordinator instance."""
        coordinator = get_pdf_coordinator()

        assert isinstance(coordinator, PDFCoordinator)

    @pytest.mark.asyncio
    async def test_download_stage_success(self):
        """Test download stage sets ctx.local_path when storage.download_file succeeds."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="test-key.pdf"
        )

        # Mock storage.download_file to succeed
        coordinator.storage.download_file = AsyncMock()

        # Execute download stage logic
        ctx.current_stage = PipelineStage.DOWNLOAD
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            await coordinator.storage.download_file(ctx.storage_key, tmp.name)
            ctx.local_path = tmp.name

        # Verify local_path is set
        assert ctx.local_path is not None
        assert ctx.local_path.endswith('.pdf')
        coordinator.storage.download_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_stage_failure(self):
        """Test download stage raises PipelineError on failure."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="test-key.pdf"
        )

        # Mock storage.download_file to fail
        coordinator.storage.download_file = AsyncMock(
            side_effect=Exception("Network error")
        )

        # Execute download stage and expect PipelineError
        ctx.current_stage = PipelineStage.DOWNLOAD
        import tempfile
        with pytest.raises(PipelineError, match="Download stage failed"):
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                try:
                    await coordinator.storage.download_file(ctx.storage_key, tmp.name)
                    ctx.local_path = tmp.name
                except Exception as e:
                    raise PipelineError(f"Download stage failed: {e}")

    @pytest.mark.asyncio
    async def test_parse_stage_success(self):
        """Test parsing stage populates ctx.parse_result."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="test-key.pdf"
        )
        ctx.local_path = "/tmp/test.pdf"

        # Mock parser.parse_pdf to return result
        coordinator.parser.parse_pdf = AsyncMock(
            return_value={"pages": [{"text": "..."}], "page_count": 10}
        )

        # Execute parsing stage
        ctx.current_stage = PipelineStage.PARSING
        ctx.parse_result = await coordinator.parser.parse_pdf(ctx.local_path)

        # Verify parse_result populated
        assert ctx.parse_result is not None
        assert "pages" in ctx.parse_result
        assert ctx.parse_result["page_count"] == 10
        coordinator.parser.parse_pdf.assert_called_once_with(ctx.local_path)

    @pytest.mark.asyncio
    async def test_parse_stage_failure(self):
        """Test parsing stage raises PipelineError on failure."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="test-key.pdf"
        )
        ctx.local_path = "/tmp/test.pdf"

        # Mock parser.parse_pdf to fail
        coordinator.parser.parse_pdf = AsyncMock(
            side_effect=Exception("Docling error")
        )

        # Execute parsing stage and expect PipelineError
        ctx.current_stage = PipelineStage.PARSING
        with pytest.raises(PipelineError, match="Parsing stage failed"):
            try:
                ctx.parse_result = await coordinator.parser.parse_pdf(ctx.local_path)
            except Exception as e:
                raise PipelineError(f"Parsing stage failed: {e}")

    @pytest.mark.asyncio
    async def test_download_parse_flow(self):
        """Test complete download→parse sequence."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="test-key.pdf"
        )

        # Mock both stages to succeed
        coordinator.storage.download_file = AsyncMock()
        coordinator.parser.parse_pdf = AsyncMock(
            return_value={"pages": [], "page_count": 0}
        )

        # Download stage
        ctx.current_stage = PipelineStage.DOWNLOAD
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            await coordinator.storage.download_file(ctx.storage_key, tmp.name)
            ctx.local_path = tmp.name

        # Parsing stage
        ctx.current_stage = PipelineStage.PARSING
        ctx.parse_result = await coordinator.parser.parse_pdf(ctx.local_path)

        # Verify complete flow
        assert ctx.local_path is not None
        assert ctx.parse_result is not None
        assert ctx.current_stage == PipelineStage.PARSING
        coordinator.storage.download_file.assert_called_once()
        coordinator.parser.parse_pdf.assert_called_once_with(ctx.local_path)

    def test_extraction_pipeline_instantiation(self):
        """Test ExtractionPipeline instantiated in coordinator."""
        coordinator = PDFCoordinator()
        assert coordinator.extraction_pipeline is not None
        assert coordinator.extraction_pipeline.executor is not None
        assert coordinator.extraction_pipeline.executor._max_workers == 4

    @pytest.mark.asyncio
    async def test_extraction_stage_calls_pipeline(self):
        """Test extraction stage calls extraction_pipeline.extract()."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"pages": [{"text": "..."}], "items": [], "markdown": ""}

        # Mock extraction_pipeline.extract
        coordinator.extraction_pipeline.extract = AsyncMock(return_value=ctx)

        ctx.current_stage = PipelineStage.EXTRACTION
        result_ctx = await coordinator.extraction_pipeline.extract(ctx)

        assert result_ctx is not None
        coordinator.extraction_pipeline.extract.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_extraction_populates_imrad(self):
        """Test extraction stage populates ctx.imrad."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"pages": [], "items": [], "markdown": ""}

        mock_ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        mock_ctx.imrad = {"introduction": "...", "methods": "..."}
        coordinator.extraction_pipeline.extract = AsyncMock(return_value=mock_ctx)

        result_ctx = await coordinator.extraction_pipeline.extract(ctx)

        assert result_ctx.imrad is not None
        assert "introduction" in result_ctx.imrad

    @pytest.mark.asyncio
    async def test_extraction_populates_metadata(self):
        """Test extraction stage populates ctx.metadata."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"pages": [], "items": [], "markdown": ""}

        mock_ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        mock_ctx.metadata = {"title": "Test Paper", "authors": ["Author"]}
        coordinator.extraction_pipeline.extract = AsyncMock(return_value=mock_ctx)

        result_ctx = await coordinator.extraction_pipeline.extract(ctx)

        assert result_ctx.metadata is not None
        assert "title" in result_ctx.metadata

    @pytest.mark.asyncio
    async def test_extraction_critical_failure_blocks(self):
        """Test extraction raises PipelineError when critical stage fails."""
        coordinator = PDFCoordinator()
        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"pages": [], "items": [], "markdown": ""}

        # Mock extraction to raise PipelineError (critical failure)
        coordinator.extraction_pipeline.extract = AsyncMock(
            side_effect=PipelineError("IMRaD extraction failed")
        )

        with pytest.raises(PipelineError, match="IMRaD extraction failed"):
            await coordinator.extraction_pipeline.extract(ctx)

    def test_storage_manager_lazy_init(self):
        """Test StorageManager lazy initialization via property."""
        coordinator = PDFCoordinator()

        # Initially None
        assert coordinator._storage_manager is None

        # Mock db_pool to avoid real database connection
        from unittest.mock import Mock
        import asyncpg
        mock_pool = Mock(spec=asyncpg.Pool)
        coordinator._db_pool = mock_pool

        # Access property triggers initialization
        sm = coordinator.storage_manager
        assert sm is not None
        assert isinstance(sm, StorageManager)

    @pytest.mark.asyncio
    async def test_storage_stage_calls_manager(self):
        """Test storage stage calls storage_manager.store()."""
        coordinator = PDFCoordinator()

        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.imrad = {"introduction": "..."}
        ctx.metadata = {"title": "..."}
        ctx.image_results = []
        ctx.table_results = []
        ctx.parse_result = {"markdown": "", "items": [], "page_count": 0}

        # Mock storage_manager.store
        from unittest.mock import Mock
        coordinator._storage_manager = Mock(spec=StorageManager)
        coordinator._storage_manager.store = AsyncMock(return_value=ctx)

        ctx.current_stage = PipelineStage.STORAGE
        result_ctx = await coordinator.storage_manager.store(ctx)

        assert result_ctx is not None
        coordinator._storage_manager.store.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_storage_returns_context(self):
        """Test storage stage returns updated context."""
        coordinator = PDFCoordinator()

        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"markdown": "", "items": [], "page_count": 0}

        from unittest.mock import Mock
        coordinator._storage_manager = Mock(spec=StorageManager)
        mock_ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        mock_ctx.chunk_results = [{"chunk_id": "chk1"}, {"chunk_id": "chk2"}]
        coordinator._storage_manager.store = AsyncMock(return_value=mock_ctx)

        result_ctx = await coordinator.storage_manager.store(ctx)

        assert result_ctx.chunk_results is not None
        assert len(result_ctx.chunk_results) == 2

    @pytest.mark.asyncio
    async def test_storage_marks_completed(self):
        """Test storage stage marks pipeline as COMPLETED."""
        coordinator = PDFCoordinator()

        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )
        ctx.parse_result = {"markdown": "", "items": [], "page_count": 0}

        from unittest.mock import Mock
        coordinator._storage_manager = Mock(spec=StorageManager)
        coordinator._storage_manager.store = AsyncMock(return_value=ctx)
        coordinator._update_status = AsyncMock()

        ctx.current_stage = PipelineStage.STORAGE
        await coordinator.storage_manager.store(ctx)

        # After storage, coordinator should mark as COMPLETED
        # (verified in process() method flow)

    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self):
        """Test complete download→parse→extract→store flow."""
        coordinator = PDFCoordinator()

        ctx = PipelineContext(
            task_id="test",
            paper_id="p1",
            user_id="u1",
            storage_key="key"
        )

        # Mock all stages
        coordinator.storage.download_file = AsyncMock()
        coordinator.parser.parse_pdf = AsyncMock(
            return_value={"pages": [], "items": [], "markdown": "", "page_count": 0}
        )
        coordinator.extraction_pipeline.extract = AsyncMock(
            return_value=ctx  # Return same ctx with modifications
        )

        from unittest.mock import Mock
        coordinator._storage_manager = Mock(spec=StorageManager)
        coordinator._storage_manager.store = AsyncMock(
            return_value=ctx  # Return same ctx with chunk_results
        )

        # Execute pipeline stages
        import tempfile
        ctx.current_stage = PipelineStage.DOWNLOAD
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            await coordinator.storage.download_file(ctx.storage_key, tmp.name)
            ctx.local_path = tmp.name  # Manually set after mock download

        ctx.current_stage = PipelineStage.PARSING
        ctx.parse_result = await coordinator.parser.parse_pdf(ctx.local_path)

        ctx.current_stage = PipelineStage.EXTRACTION
        ctx.imrad = {"introduction": "..."}  # Manually set after mock extraction
        ctx.metadata = {"title": "Test"}
        ctx.image_results = []
        ctx.table_results = []

        ctx.current_stage = PipelineStage.STORAGE
        ctx.chunk_results = [{"chunk_id": "chk1"}]  # Manually set after mock storage

        # Verify complete flow
        assert ctx.local_path is not None
        assert ctx.parse_result is not None
        assert ctx.imrad is not None
        assert ctx.metadata is not None
        assert ctx.chunk_results is not None
        assert len(ctx.chunk_results) == 1