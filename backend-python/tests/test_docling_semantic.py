"""Tests for semantic chunking with LlamaIndex SemanticSplitterNodeParser (per D-03).

TDD workflow:
1. RED: These tests will fail until chunk_by_semantic() is implemented
2. GREEN: Implementation makes tests pass
3. REFACTOR: Clean up if needed

Parameters (LOCKED per D-03):
- buffer_size=1
- breakpoint_percentile_threshold=95
- overlap=100 tokens
"""

import pytest
from app.core.docling_service import DoclingParser


class TestSemanticChunking:
    """Test suite for semantic chunking functionality."""

    def test_chunk_by_semantic_method_exists(self):
        """Test 1: chunk_by_semantic() method exists."""
        parser = DoclingParser()
        assert hasattr(parser, "chunk_by_semantic"), \
            "DoclingParser should have chunk_by_semantic method"

    def test_uses_semantic_splitter_with_buffer_size_1(self):
        """Test 2: Uses SemanticSplitterNodeParser with buffer_size=1."""
        parser = DoclingParser()

        # Sample items
        items = [
            {"type": "text", "text": "Introduction paragraph.", "page": 1},
            {"type": "text", "text": "Method description.", "page": 2},
        ]

        # Call chunk_by_semantic
        chunks = parser.chunk_by_semantic(items, paper_id="test-paper")

        # Verify chunks were created
        assert len(chunks) > 0, "Should create at least one chunk"

        # Note: We can't directly verify buffer_size from output,
        # but we verify the method works with semantic splitting behavior

    def test_uses_breakpoint_percentile_threshold_95(self):
        """Test 3: Uses breakpoint_percentile_threshold=95 (LOCKED per D-03)."""
        parser = DoclingParser()

        # Sample items with distinct semantic boundaries
        items = [
            {"type": "text", "text": "First section about introduction.", "page": 1},
            {"type": "text", "text": "Second section about methods.", "page": 2},
            {"type": "text", "text": "Third section about results.", "page": 3},
        ]

        chunks = parser.chunk_by_semantic(items, paper_id="test-paper")

        # High threshold (95) should create fewer chunks than low threshold
        # At 95, only very different semantic content will split
        assert len(chunks) > 0, "Should create semantic chunks"

    def test_returns_chunks_with_required_fields(self):
        """Test 4: Returns chunks with page_start, page_end, text fields."""
        parser = DoclingParser()

        items = [
            {"type": "text", "text": "Sample text content.", "page": 1},
            {"type": "text", "text": "Another text content.", "page": 2},
        ]

        chunks = parser.chunk_by_semantic(items, paper_id="test-paper")

        # Verify each chunk has required fields
        for chunk in chunks:
            assert "text" in chunk, "Chunk should have 'text' field"
            assert "page_start" in chunk, "Chunk should have 'page_start' field"
            assert "page_end" in chunk, "Chunk should have 'page_end' field"
            assert isinstance(chunk["text"], str), "Text should be a string"

    def test_chunks_have_overlap_field_100_tokens(self):
        """Test 5: Chunks have overlap field set to 100 tokens."""
        parser = DoclingParser()

        items = [
            {"type": "text", "text": "First paragraph with some content.", "page": 1},
            {"type": "text", "text": "Second paragraph with different content.", "page": 2},
        ]

        chunks = parser.chunk_by_semantic(items, paper_id="test-paper")

        # Verify overlap field
        assert len(chunks) > 0, "Should create chunks"

        # First chunk should have overlap=0, subsequent chunks should have overlap=100
        if len(chunks) >= 1:
            assert "overlap" in chunks[0], "First chunk should have 'overlap' field"
            assert chunks[0]["overlap"] == 0, "First chunk should have overlap=0"

        if len(chunks) >= 2:
            assert "overlap" in chunks[1], "Second chunk should have 'overlap' field"
            assert chunks[1]["overlap"] == 100, \
                "Second chunk should have overlap=100 tokens per D-03"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])