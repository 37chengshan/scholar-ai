"""Unit tests for citation helper methods in agentic_retrieval.py.

Tests for:
- _build_context_with_citations(): builds context with citation markers
- _collect_sources(): includes citation field in source objects

TDD Approach:
1. Write tests first
2. Run tests - FAIL
3. Implement methods
4. Run tests - PASS
"""

import pytest
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator


class TestBuildContextWithCitations:
    """Tests for _build_context_with_citations method."""

    @pytest.fixture
    def orchestrator(self) -> AgenticRetrievalOrchestrator:
        """Create orchestrator instance."""
        return AgenticRetrievalOrchestrator()

    def test_basic_citation_format(self, orchestrator: AgenticRetrievalOrchestrator):
        """Test basic citation format with paper_title and section."""
        chunks = [
            {
                "content": "YOLOv1 introduces a unified object detection framework.",
                "paper_title": "YOLOv1 Paper",
                "section": "Introduction",
                "page": 1,
                "similarity": 0.75,
            },
            {
                "content": "The architecture uses a single neural network.",
                "paper_title": "YOLOv1 Paper",
                "section": "Method",
                "page": 3,
                "similarity": 0.80,
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        assert "[YOLOv1 Paper, Introduction]" in result
        assert "[YOLOv1 Paper, Method]" in result
        assert "YOLOv1 introduces" in result
        assert "single neural network" in result

    def test_citation_with_page_when_section_missing(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test citation falls back to Page when section is missing."""
        chunks = [
            {
                "content": "Some important finding here.",
                "paper_title": "Test Paper",
                "section": None,
                "page": 5,
                "similarity": 0.70,
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        assert "[Test Paper, Page 5]" in result
        assert "Some important finding" in result

    def test_high_similarity_chunk_extended_length(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test high similarity (>0.85) chunks get extended to 300 chars."""
        long_content = (
            "This is a very important and highly relevant chunk that contains "
            "detailed information about the methodology and should be preserved "
            "in its entirety because it has high similarity score. The content "
            "continues here with more details about the implementation specifics "
            "and experimental results that demonstrate the effectiveness of the "
            "proposed approach. We need to ensure this content is preserved well."
        )
        chunks = [
            {
                "content": long_content,
                "paper_title": "Important Paper",
                "section": "Results",
                "page": 10,
                "similarity": 0.90,  # > 0.85 threshold
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        # Should contain ~300 chars of content (extended for high similarity)
        assert len(result) > 250  # Has substantial content preserved
        assert "[Important Paper, Results]" in result

    def test_normal_chunk_truncated_to_sentence_boundary(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test normal chunks truncated to ~200 chars at sentence boundary."""
        long_content = (
            "This is a normal chunk. It contains multiple sentences here. "
            "The second sentence continues the discussion. The third sentence "
            "adds more context about the topic. The fourth sentence provides "
            "additional details. The fifth sentence wraps up the paragraph."
        )
        chunks = [
            {
                "content": long_content,
                "paper_title": "Normal Paper",
                "section": "Discussion",
                "page": 8,
                "similarity": 0.75,  # Below 0.85 threshold
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        # Should truncate around 200 chars at sentence boundary
        assert "[Normal Paper, Discussion]" in result
        # Should not contain the fifth sentence (too long)
        assert "fifth sentence" not in result

    def test_empty_chunks_returns_empty_string(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test empty chunks list returns empty string."""
        result = orchestrator._build_context_with_citations([])
        assert result == ""

    def test_missing_paper_title_falls_back_to_paper_id(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test citation uses paper_id when paper_title is missing."""
        chunks = [
            {
                "content": "Content without title.",
                "paper_title": None,
                "paper_id": "paper-uuid-123",
                "section": "Abstract",
                "page": 1,
                "similarity": 0.70,
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        assert "[paper-uuid-123, Abstract]" in result

    def test_multiple_chunks_formatted_separately(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test multiple chunks are formatted with clear separation."""
        chunks = [
            {
                "content": "First chunk content.",
                "paper_title": "Paper A",
                "section": "Intro",
                "page": 1,
                "similarity": 0.80,
            },
            {
                "content": "Second chunk content.",
                "paper_title": "Paper B",
                "section": "Method",
                "page": 5,
                "similarity": 0.75,
            },
            {
                "content": "Third chunk content.",
                "paper_title": "Paper A",
                "section": "Results",
                "page": 10,
                "similarity": 0.88,
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        assert "[Paper A, Intro]" in result
        assert "[Paper B, Method]" in result
        assert "[Paper A, Results]" in result
        # Each chunk should be clearly separated
        assert "First chunk content" in result
        assert "Second chunk content" in result
        assert "Third chunk content" in result


class TestCollectSourcesWithCitations:
    """Tests for _collect_sources method with citation field."""

    @pytest.fixture
    def orchestrator(self) -> AgenticRetrievalOrchestrator:
        """Create orchestrator instance."""
        return AgenticRetrievalOrchestrator()

    def test_source_includes_citation_field(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test each source includes citation field."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "sub_question": "What is YOLO?",
                        "chunks": [
                            {
                                "id": "chunk-1",
                                "paper_id": "yolo-paper",
                                "paper_title": "YOLO: Unified Detection",
                                "content": "YOLO is a unified framework.",
                                "section": "Introduction",
                                "page": 1,
                                "similarity": 0.85,
                            }
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert len(sources) == 1
        assert "citation" in sources[0]
        assert sources[0]["citation"] == "[YOLO: Unified Detection, Introduction]"

    def test_citation_fallback_to_page_when_no_section(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test citation uses Page when section is missing."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "chunks": [
                            {
                                "id": "chunk-2",
                                "paper_id": "test-paper",
                                "paper_title": "Test Paper",
                                "content": "Some content.",
                                "section": None,
                                "page": 7,
                                "similarity": 0.70,
                            }
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert sources[0]["citation"] == "[Test Paper, Page 7]"

    def test_citation_fallback_to_paper_id_when_no_title(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test citation uses paper_id when paper_title is missing."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "chunks": [
                            {
                                "id": "chunk-3",
                                "paper_id": "uuid-abc-123",
                                "paper_title": None,
                                "content": "Content here.",
                                "section": "Results",
                                "page": 5,
                                "similarity": 0.75,
                            }
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert sources[0]["citation"] == "[uuid-abc-123, Results]"

    def test_sources_deduplicated_by_chunk_id(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test duplicate chunks are deduplicated."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "chunks": [
                            {
                                "id": "chunk-same",
                                "paper_id": "paper-1",
                                "paper_title": "Paper 1",
                                "content": "Shared content.",
                                "section": "Intro",
                                "page": 1,
                                "similarity": 0.80,
                            }
                        ],
                        "success": True,
                    }
                ],
            },
            {
                "round": 2,
                "results": [
                    {
                        "chunks": [
                            {
                                "id": "chunk-same",  # Same ID as round 1
                                "paper_id": "paper-1",
                                "paper_title": "Paper 1",
                                "content": "Shared content.",
                                "section": "Intro",
                                "page": 1,
                                "similarity": 0.82,
                            }
                        ],
                        "success": True,
                    }
                ],
            },
        ]

        sources = orchestrator._collect_sources(all_results)

        # Should deduplicate - only one source
        assert len(sources) == 1
        assert sources[0]["citation"] == "[Paper 1, Intro]"

    def test_sources_sorted_by_similarity(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test sources are sorted by similarity descending."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "chunks": [
                            {
                                "id": "chunk-low",
                                "paper_id": "paper-1",
                                "paper_title": "Paper A",
                                "content": "Low similarity.",
                                "section": "Intro",
                                "similarity": 0.60,
                            },
                            {
                                "id": "chunk-high",
                                "paper_id": "paper-2",
                                "paper_title": "Paper B",
                                "content": "High similarity.",
                                "section": "Results",
                                "similarity": 0.90,
                            },
                            {
                                "id": "chunk-mid",
                                "paper_id": "paper-3",
                                "paper_title": "Paper C",
                                "content": "Mid similarity.",
                                "section": "Method",
                                "similarity": 0.75,
                            },
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert len(sources) == 3
        # Sorted by similarity descending
        assert sources[0]["similarity"] == 0.90
        assert sources[1]["similarity"] == 0.75
        assert sources[2]["similarity"] == 0.60
        # Citations present
        assert sources[0]["citation"] == "[Paper B, Results]"
        assert sources[1]["citation"] == "[Paper C, Method]"
        assert sources[2]["citation"] == "[Paper A, Intro]"

    def test_empty_results_returns_empty_list(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test empty results returns empty sources list."""
        sources = orchestrator._collect_sources([])
        assert sources == []

    def test_failed_results_skipped(self, orchestrator: AgenticRetrievalOrchestrator):
        """Test failed results are skipped."""
        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "chunks": [],
                        "success": False,
                        "error": "Search failed",
                    },
                    {
                        "chunks": [
                            {
                                "id": "chunk-valid",
                                "paper_id": "paper-ok",
                                "paper_title": "Valid Paper",
                                "content": "Valid content.",
                                "section": "Intro",
                                "similarity": 0.80,
                            }
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert len(sources) == 1
        assert sources[0]["citation"] == "[Valid Paper, Intro]"