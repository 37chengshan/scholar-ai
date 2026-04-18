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
                "text": "YOLOv1 introduces a unified object detection framework.",
                "paper_title": "YOLOv1 Paper",
                "section": "Introduction",
                "page_num": 1,
                "score": 0.75,
            },
            {
                "text": "The architecture uses a single neural network.",
                "paper_title": "YOLOv1 Paper",
                "section": "Method",
                "page_num": 3,
                "score": 0.80,
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
                "text": "Some important finding here.",
                "paper_title": "Test Paper",
                "section": None,
                "page_num": 5,
                "score": 0.70,
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        assert "[Test Paper, Page 5]" in result
        assert "Some important finding" in result

    def test_high_score_chunk_extended_length(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test high score (>0.85) chunks get extended to 300 chars."""
        long_content = (
            "This is a very important and highly relevant chunk that contains "
            "detailed information about the methodology and should be preserved "
            "in its entirety because it has high score score. The content "
            "continues here with more details about the implementation specifics "
            "and experimental results that demonstrate the effectiveness of the "
            "proposed approach. We need to ensure this content is preserved well."
        )
        chunks = [
            {
                "text": long_content,
                "paper_title": "Important Paper",
                "section": "Results",
                "page_num": 10,
                "score": 0.90,  # > 0.85 threshold
            },
        ]

        result = orchestrator._build_context_with_citations(chunks)

        # Should contain ~300 chars of content (extended for high score)
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
                "text": long_content,
                "paper_title": "Normal Paper",
                "section": "Discussion",
                "page_num": 8,
                "score": 0.75,  # Below 0.85 threshold
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
                "text": "Content without title.",
                "paper_title": None,
                "paper_id": "paper-uuid-123",
                "section": "Abstract",
                "page_num": 1,
                "score": 0.70,
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
                "text": "First chunk content.",
                "paper_title": "Paper A",
                "section": "Intro",
                "page_num": 1,
                "score": 0.80,
            },
            {
                "text": "Second chunk content.",
                "paper_title": "Paper B",
                "section": "Method",
                "page_num": 5,
                "score": 0.75,
            },
            {
                "text": "Third chunk content.",
                "paper_title": "Paper A",
                "section": "Results",
                "page_num": 10,
                "score": 0.88,
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
                                "text": "YOLO is a unified framework.",
                                "section": "Introduction",
                                "page_num": 1,
                                "score": 0.85,
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
                                "text": "Some content.",
                                "section": None,
                                "page_num": 7,
                                "score": 0.70,
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
                                "text": "Content here.",
                                "section": "Results",
                                "page_num": 5,
                                "score": 0.75,
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
                                "text": "Shared content.",
                                "section": "Intro",
                                "page_num": 1,
                                "score": 0.80,
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
                                "text": "Shared content.",
                                "section": "Intro",
                                "page_num": 1,
                                "score": 0.82,
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

    def test_sources_sorted_by_score(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test sources are sorted by score descending."""
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
                                "text": "Low score.",
                                "section": "Intro",
                                "page_num": 1,
                                "score": 0.60,
                            },
                            {
                                "id": "chunk-high",
                                "paper_id": "paper-2",
                                "paper_title": "Paper B",
                                "text": "High score.",
                                "section": "Results",
                                "page_num": 2,
                                "score": 0.90,
                            },
                            {
                                "id": "chunk-mid",
                                "paper_id": "paper-3",
                                "paper_title": "Paper C",
                                "text": "Mid score.",
                                "section": "Method",
                                "page_num": 3,
                                "score": 0.75,
                            },
                        ],
                        "success": True,
                    }
                ],
            }
        ]

        sources = orchestrator._collect_sources(all_results)

        assert len(sources) == 3
        # Sorted by score descending
        assert sources[0]["score"] == 0.90
        assert sources[1]["score"] == 0.75
        assert sources[2]["score"] == 0.60
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
                                "text": "Valid content.",
                                "section": "Intro",
                                "page_num": 1,
                                "score": 0.80,
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


class TestValidateAndFixCitations:
    """Tests for _validate_and_fix_citations post-processing method."""

    @pytest.fixture
    def orchestrator(self) -> AgenticRetrievalOrchestrator:
        """Create orchestrator instance."""
        return AgenticRetrievalOrchestrator()

    def test_extract_citation_markers(self, orchestrator: AgenticRetrievalOrchestrator):
        """Test extraction of [Paper, Section] citation markers from answer."""
        answer = """## YOLO Evolution

YOLOv1 introduced the unified detection framework [YOLOv1 Paper, Introduction].
Key improvements include:
- Faster inference speed [YOLOv2 Paper, Method]
- Better accuracy with anchor boxes [YOLOv2 Paper, Results]
"""

        citations = orchestrator._extract_citations_from_answer(answer)

        assert len(citations) == 3
        assert ("YOLOv1 Paper", "Introduction") in citations
        assert ("YOLOv2 Paper", "Method") in citations
        assert ("YOLOv2 Paper", "Results") in citations

    def test_calculate_citation_density(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test citation density calculation."""
        answer = """Content with [Paper A, Section 1] and [Paper B, Section 2].
More content here [Paper C, Section 3]."""

        # 3 citations, ~70 words -> density ~0.04
        density = orchestrator._calculate_citation_density(answer)

        # Citation density should be positive
        assert density > 0
        # Approximate check: 3 citations in ~20 words of content
        assert density >= 0.1  # At least 10% citation rate

    def test_citation_density_below_threshold_triggers_fallback(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test low citation density triggers fallback answer generation."""
        answer = "This is a long answer without any citations at all. " * 10

        # 0 citations, many words -> very low density
        citations = orchestrator._extract_citations_from_answer(answer)
        assert len(citations) == 0

        # Should need fallback (density < threshold)
        chunks = [
            {
                "text": "YOLOv1 content here.",
                "paper_title": "YOLOv1",
                "section": "Intro",
                "score": 0.80,
            },
            {
                "text": "YOLOv2 content here.",
                "paper_title": "YOLOv2",
                "section": "Method",
                "score": 0.75,
            },
        ]

        needs_fallback = orchestrator._needs_citation_fallback(answer, len(chunks))
        assert needs_fallback is True

    def test_citation_density_above_threshold_no_fallback(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test sufficient citation density does not trigger fallback."""
        answer = "Answer with [Paper A, Intro] and [Paper B, Method] citations."

        # 2 citations in short answer -> good density
        chunks = [
            {"text": "Content", "paper_title": "Paper A", "section": "Intro"},
            {"text": "Content", "paper_title": "Paper B", "section": "Method"},
        ]

        needs_fallback = orchestrator._needs_citation_fallback(answer, len(chunks))
        assert needs_fallback is False

    def test_validate_returns_original_answer_when_sufficient_citations(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test validation returns original answer when citations are sufficient."""
        answer = """## Summary

Key findings [Paper A, Results] show improvements.
Methods described in [Paper B, Method] are effective.
"""

        chunks = [
            {
                "id": "c1",
                "text": "Findings content",
                "paper_title": "Paper A",
                "section": "Results",
                "score": 0.85,
            },
            {
                "id": "c2",
                "text": "Methods content",
                "paper_title": "Paper B",
                "section": "Method",
                "score": 0.80,
            },
        ]

        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "sub_question": "Test query",
                        "chunks": chunks,
                        "success": True,
                    }
                ],
            }
        ]

        validated = orchestrator._validate_and_fix_citations(
            answer=answer,
            all_results=all_results,
            query="Test query",
        )

        # Should return original answer when citations sufficient
        assert validated == answer

    def test_validate_returns_fallback_when_insufficient_citations(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test validation returns fallback answer when citations insufficient."""
        answer = "This is a long answer without any proper citation markers."

        chunks = [
            {
                "id": "c1",
                "text": "YOLOv1 introduced unified detection framework.",
                "paper_title": "YOLOv1 Paper",
                "section": "Introduction",
                "page_num": 1,
                "score": 0.85,
            },
            {
                "id": "c2",
                "text": "YOLOv2 improved with anchor boxes.",
                "paper_title": "YOLOv2 Paper",
                "section": "Method",
                "page_num": 2,
                "score": 0.80,
            },
        ]

        all_results = [
            {
                "round": 1,
                "results": [
                    {
                        "sub_question": "YOLO evolution",
                        "chunks": chunks,
                        "success": True,
                    }
                ],
            }
        ]

        validated = orchestrator._validate_and_fix_citations(
            answer=answer,
            all_results=all_results,
            query="YOLO evolution",
        )

        # Should return fallback answer with proper citations
        assert "[YOLOv1 Paper, Introduction]" in validated
        assert "[YOLOv2 Paper, Method]" in validated


class TestBuildFallbackAnswer:
    """Tests for _build_fallback_answer method."""

    @pytest.fixture
    def orchestrator(self) -> AgenticRetrievalOrchestrator:
        """Create orchestrator instance."""
        return AgenticRetrievalOrchestrator()

    def test_fallback_groups_chunks_by_section(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback answer groups chunks by section."""
        chunks = [
            {
                "text": "YOLOv1 intro content.",
                "paper_title": "YOLOv1",
                "section": "Introduction",
                "page_num": 1,
                "score": 0.80,
            },
            {
                "text": "YOLOv1 method content.",
                "paper_title": "YOLOv1",
                "section": "Method",
                "page_num": 2,
                "score": 0.75,
            },
            {
                "text": "YOLOv2 intro content.",
                "paper_title": "YOLOv2",
                "section": "Introduction",
                "page_num": 3,
                "score": 0.85,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="YOLO comparison",
        )

        # Should have section headers
        assert "Introduction" in fallback
        assert "Method" in fallback
        # Should have citations for each chunk
        assert "[YOLOv1, Introduction]" in fallback
        assert "[YOLOv1, Method]" in fallback
        assert "[YOLOv2, Introduction]" in fallback

    def test_fallback_uses_citation_format(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback uses [Paper Title, Section] citation format."""
        chunks = [
            {
                "text": "Important finding.",
                "paper_title": "Test Paper",
                "section": "Results",
                "page_num": 5,
                "score": 0.90,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="What are the results?",
        )

        # Must use exact citation format
        assert "[Test Paper, Results]" in fallback

    def test_fallback_falls_back_to_page_when_no_section(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback uses Page format when section is missing."""
        chunks = [
            {
                "text": "Content without section.",
                "paper_title": "Paper X",
                "section": None,
                "page_num": 10,
                "score": 0.70,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="Query",
        )

        assert "[Paper X, Page 10]" in fallback

    def test_fallback_uses_paper_id_when_no_title(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback uses paper_id when paper_title is missing."""
        chunks = [
            {
                "text": "Content without title.",
                "paper_title": None,
                "paper_id": "uuid-123",
                "section": "Abstract",
                "page_num": 1,
                "score": 0.75,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="Query",
        )

        assert "[uuid-123, Abstract]" in fallback

    def test_fallback_structure_has_headers_and_bullets(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback answer uses proper structure with headers and bullets."""
        chunks = [
            {
                "text": "First finding.",
                "paper_title": "Paper A",
                "section": "Results",
                "page_num": 1,
                "score": 0.80,
            },
            {
                "text": "Second finding.",
                "paper_title": "Paper B",
                "section": "Results",
                "page_num": 2,
                "score": 0.75,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="What are the findings?",
        )

        # Should have header format
        assert "##" in fallback or "Results" in fallback
        # Should use bullet format for items
        assert "-" in fallback or "*" in fallback

    def test_fallback_empty_chunks_returns_no_info_message(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback with empty chunks returns appropriate message."""
        fallback = orchestrator._build_fallback_answer(
            chunks=[],
            query="Query",
        )

        assert "No relevant information" in fallback or "no information" in fallback.lower()

    def test_fallback_truncates_long_content(
        self, orchestrator: AgenticRetrievalOrchestrator
    ):
        """Test fallback truncates very long chunk content."""
        long_content = "Very long content. " * 50  # ~1000 chars
        chunks = [
            {
                "text": long_content,
                "paper_title": "Long Paper",
                "section": "Intro",
                "page_num": 1,
                "score": 0.80,
            },
        ]

        fallback = orchestrator._build_fallback_answer(
            chunks=chunks,
            query="Query",
        )

        # Should truncate content (not include full 1000 chars)
        assert len(fallback) < len(long_content) + 100  # +100 for structure
        # Should still have citation
        assert "[Long Paper, Intro]" in fallback