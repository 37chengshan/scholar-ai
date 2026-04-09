"""Unit tests for Paper model.

Tests Paper model creation, constraints, relationships, and default values.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.paper import Paper, PaperChunk


class TestPaperModel:
    """Tests for Paper model."""

    def test_paper_creation_basic(self):
        """Test Paper model can be instantiated with basic fields."""
        paper = Paper(
            id=str(uuid4()),
            title="Test Paper Title",
            user_id="user-123",
            status="pending",  # Set explicitly since server default
            starred=False,  # Set explicitly since server default
            authors=[],  # Set explicitly since server default
        )
        assert paper.title == "Test Paper Title"
        assert paper.user_id == "user-123"
        assert paper.status == "pending"
        assert paper.starred is False
        assert paper.authors == []

    def test_paper_creation_with_metadata(self):
        """Test Paper model with all metadata fields."""
        paper = Paper(
            id=str(uuid4()),
            title="Advanced Paper",
            authors=["Author One", "Author Two", "Author Three"],
            year=2024,
            abstract="This is the abstract of the paper.",
            doi="10.1000/test.123",
            arxiv_id="2401.12345",
            venue="International Conference on AI",
            citations=42,
            user_id="user-456",
            keywords=["machine learning", "deep learning", "NLP"],
        )
        assert len(paper.authors) == 3
        assert paper.authors[0] == "Author One"
        assert paper.year == 2024
        assert paper.abstract == "This is the abstract of the paper."
        assert paper.doi == "10.1000/test.123"
        assert paper.arxiv_id == "2401.12345"
        assert paper.venue == "International Conference on AI"
        assert paper.citations == 42
        assert len(paper.keywords) == 3
        assert "machine learning" in paper.keywords

    def test_paper_with_content(self):
        """Test Paper with content and IMRaD structure."""
        imrad = {
            "introduction": {"content": "Introduction text...", "page_start": 1, "page_end": 2},
            "methods": {"content": "Methods text...", "page_start": 3, "page_end": 5},
            "results": {"content": "Results text...", "page_start": 6, "page_end": 8},
            "discussion": {"content": "Discussion text...", "page_start": 9, "page_end": 10},
        }
        paper = Paper(
            id=str(uuid4()),
            title="Paper with Content",
            content="Full paper content here...",
            imrad_json=imrad,
            user_id="user-123",
        )
        assert paper.content == "Full paper content here..."
        assert paper.imrad_json is not None
        assert "introduction" in paper.imrad_json
        assert paper.imrad_json["methods"]["page_start"] == 3

    def test_paper_with_file_info(self):
        """Test Paper with file information."""
        paper = Paper(
            id=str(uuid4()),
            title="Paper with File",
            pdf_url="https://example.com/paper.pdf",
            pdf_path="/data/papers/paper.pdf",
            storage_key="uploads/user-123/paper.pdf",
            file_size=2048576,  # 2MB
            page_count=15,
            user_id="user-123",
        )
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.pdf_path == "/data/papers/paper.pdf"
        assert paper.storage_key == "uploads/user-123/paper.pdf"
        assert paper.file_size == 2048576
        assert paper.page_count == 15

    def test_paper_status_values(self):
        """Test Paper status can have various values."""
        statuses = ["pending", "processing", "completed", "failed"]
        for status in statuses:
            paper = Paper(
                id=str(uuid4()),
                title=f"Paper {status}",
                user_id="user-123",
            )
            paper.status = status
            assert paper.status == status

    def test_paper_starred_toggle(self):
        """Test Paper starred field can be toggled."""
        paper = Paper(
            id=str(uuid4()),
            title="Starred Paper",
            user_id="user-123",
            starred=False,
        )
        assert paper.starred is False

        paper.starred = True
        assert paper.starred is True

    def test_paper_repr(self):
        """Test Paper __repr__ method."""
        paper = Paper(
            id="paper-123",
            title="This is a very long paper title that should be truncated in repr",
            user_id="user-456",
        )
        repr_str = repr(paper)
        assert "paper-123" in repr_str
        assert "..." in repr_str  # Title should be truncated

    def test_paper_user_title_unique_constraint(self):
        """Test Paper has unique constraint on (user_id, title)."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        table = mapper.local_table
        constraint_names = [c.name for c in table.constraints]
        assert "unique_user_title" in constraint_names

    def test_paper_indexes(self):
        """Test Paper has expected indexes."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        table = mapper.local_table

        index_names = [idx.name for idx in table.indexes]
        expected_indexes = [
            "idx_papers_user_id",
            "idx_papers_starred",
            "idx_papers_batch_id",
        ]
        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"

    def test_paper_relationships_defined(self):
        """Test Paper has all expected relationships."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        rel_names = [rel.key for rel in mapper.relationships]

        expected_relationships = [
            "user",
            "paper_chunks",
            "processing_task",
            "annotations",
            "reading_progress",
            "upload_history",
            "batch",
            "project",
        ]
        for rel in expected_relationships:
            assert rel in rel_names, f"Missing relationship: {rel}"

        # queries relationship was removed due to ARRAY FK issue
        assert "queries" not in rel_names


class TestPaperChunkModel:
    """Tests for PaperChunk model."""

    def test_paper_chunk_creation_basic(self):
        """Test PaperChunk can be instantiated with basic fields."""
        chunk = PaperChunk(
            id=str(uuid4()),
            content="This is a text chunk from the paper.",
            paper_id="paper-123",
            is_table=False,  # Set explicitly since server default
            is_figure=False,  # Set explicitly since server default
            is_formula=False,  # Set explicitly since server default
        )
        assert chunk.content == "This is a text chunk from the paper."
        assert chunk.paper_id == "paper-123"
        assert chunk.section is None
        assert chunk.is_table is False
        assert chunk.is_figure is False
        assert chunk.is_formula is False

    def test_paper_chunk_with_section(self):
        """Test PaperChunk with section information."""
        chunk = PaperChunk(
            id=str(uuid4()),
            content="Methods section content...",
            section="methods",
            page_start=3,
            page_end=5,
            paper_id="paper-123",
        )
        assert chunk.section == "methods"
        assert chunk.page_start == 3
        assert chunk.page_end == 5

    def test_paper_chunk_types(self):
        """Test PaperChunk can be marked as table/figure/formula."""
        # Table chunk
        table_chunk = PaperChunk(
            id=str(uuid4()),
            content="| Column 1 | Column 2 |\n|----------|----------|\n| Data 1   | Data 2   |",
            paper_id="paper-123",
            is_table=True,
            is_figure=False,
            is_formula=False,
        )
        assert table_chunk.is_table is True
        assert table_chunk.is_figure is False

        # Figure chunk
        figure_chunk = PaperChunk(
            id=str(uuid4()),
            content="Figure 1: Neural network architecture diagram",
            paper_id="paper-123",
            is_figure=True,
            is_table=False,
            is_formula=False,
        )
        assert figure_chunk.is_figure is True

        # Formula chunk
        formula_chunk = PaperChunk(
            id=str(uuid4()),
            content="E = mc^2",
            paper_id="paper-123",
            is_formula=True,
            is_table=False,
            is_figure=False,
        )
        assert formula_chunk.is_formula is True

    def test_paper_chunk_index(self):
        """Test PaperChunk has index on paper_id."""
        from sqlalchemy import inspect
        mapper = inspect(PaperChunk)
        table = mapper.local_table

        index_names = [idx.name for idx in table.indexes]
        assert "idx_paper_chunks_paper_id" in index_names

    def test_paper_chunk_repr(self):
        """Test PaperChunk __repr__ method."""
        chunk = PaperChunk(
            id="chunk-123",
            content="Test content",
            paper_id="paper-456",
        )
        repr_str = repr(chunk)
        assert "chunk-123" in repr_str
        assert "paper-456" in repr_str


class TestPaperModelIntegration:
    """Integration-style tests for Paper model relationships."""

    def test_paper_user_relationship_config(self):
        """Test Paper.user relationship configuration."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        user_rel = mapper.relationships.user
        assert user_rel.back_populates == "papers"

    def test_paper_chunks_cascade_delete(self):
        """Test Paper.paper_chunks has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        chunks_rel = mapper.relationships.paper_chunks

        assert "delete" in chunks_rel.cascade

    def test_paper_annotations_cascade_delete(self):
        """Test Paper.annotations has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        annotations_rel = mapper.relationships.annotations

        assert "delete" in annotations_rel.cascade

    def test_paper_reading_progress_cascade_delete(self):
        """Test Paper.reading_progress has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        rp_rel = mapper.relationships.reading_progress

        assert "delete" in rp_rel.cascade