"""
Tests for NotesGenerator with LiteLLM integration.

Tests the generation of IMRaD-structured reading notes using LiteLLM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


class TestNotesGenerator:
    """Test suite for NotesGenerator class."""

    @pytest.fixture
    def sample_paper_metadata(self):
        """Sample paper metadata."""
        return {
            "title": "Deep Learning for Medical Image Analysis",
            "authors": ["Zhang San", "Li Si", "Wang Wu"],
            "year": "2024",
            "venue": "Nature Medicine",
        }

    @pytest.fixture
    def sample_imrad_structure(self):
        """Sample IMRaD structure."""
        return {
            "introduction": {
                "content": "Medical imaging has become essential in modern healthcare...",
                "word_count": 500,
                "confidence": 1.0,
            },
            "methods": {
                "content": "We used a CNN architecture with 12 layers...",
                "word_count": 800,
                "confidence": 1.0,
            },
            "results": {
                "content": "The model achieved 95% accuracy on the test set...",
                "word_count": 600,
                "confidence": 1.0,
            },
            "conclusion": {
                "content": "AI can effectively assist medical diagnosis...",
                "word_count": 400,
                "confidence": 1.0,
            }
        }

    @pytest.fixture
    def mock_litellm_response(self):
        """Mock LiteLLM response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""## 1. Research Question & Motivation

This paper addresses the challenge of improving medical image analysis accuracy using deep learning techniques.

## 2. Key Contributions & Innovation Points

- Novel CNN architecture for medical imaging
- Improved accuracy over existing methods
- Comprehensive dataset from multiple hospitals

## 3. Methodology

The study employed a 12-layer CNN with specific optimizations for medical imaging data.

## 4. Main Results & Findings

- 95% accuracy achieved
- Outperformed traditional methods
- High precision and recall scores

## 5. Limitations & Future Work

Limited to 2D images; 3D imaging is future work.

## 6. Personal Takeaways

This approach shows significant promise for clinical applications."""
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=1500)
        return mock_response

    @pytest.mark.asyncio
    async def test_notes_generator_initialization(self):
        """Test NotesGenerator can be initialized."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()
        assert generator.model is not None
        assert generator.max_content_length == 15000
        assert generator.max_tokens == 2000
        assert generator.temperature == 0.3

    @pytest.mark.asyncio
    async def test_notes_generator_with_custom_model(self):
        """Test NotesGenerator with custom model."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator(model="gpt-4o")
        assert generator.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_generate_notes(self, sample_paper_metadata, sample_imrad_structure, mock_litellm_response):
        """Test generating reading notes."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_response

            notes = await generator.generate_notes(
                paper_metadata=sample_paper_metadata,
                imrad_structure=sample_imrad_structure
            )

            # Verify notes contain all 6 IMRaD sections
            assert "## 1. Research Question & Motivation" in notes
            assert "## 2. Key Contributions & Innovation Points" in notes
            assert "## 3. Methodology" in notes
            assert "## 4. Main Results & Findings" in notes
            assert "## 5. Limitations & Future Work" in notes
            assert "## 6. Personal Takeaways" in notes

            # Verify LiteLLM was called
            mock_acompletion.assert_called_once()
            call_args = mock_acompletion.call_args
            assert call_args.kwargs["model"] == generator.model
            assert call_args.kwargs["temperature"] == 0.3
            assert call_args.kwargs["max_tokens"] == 2000

    @pytest.mark.asyncio
    async def test_regenerate_notes_with_modification(self, sample_paper_metadata, sample_imrad_structure, mock_litellm_response):
        """Test regenerating notes with modification request."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_response

            notes = await generator.regenerate_notes(
                paper_metadata=sample_paper_metadata,
                imrad_structure=sample_imrad_structure,
                modification_request="Focus more on the methodology section"
            )

            # Verify notes were generated
            assert "## 1. Research Question & Motivation" in notes

            # Verify modification request was included in prompt
            call_args = mock_acompletion.call_args
            messages = call_args.kwargs["messages"]
            assert "Focus more on the methodology section" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_truncate_content(self):
        """Test content truncation."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        # Content within limit
        short_content = "Short content"
        assert generator._truncate_content(short_content) == short_content

        # Content exceeding limit
        long_content = "x" * 20000
        truncated = generator._truncate_content(long_content)
        assert len(truncated) <= 15000 + 50  # Allow for truncation message
        assert "[Content truncated" in truncated

    @pytest.mark.asyncio
    async def test_prepare_imrad_content(self, sample_imrad_structure):
        """Test preparing IMRaD content for prompt."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        prepared = generator._prepare_imrad_content(sample_imrad_structure)

        assert "introduction" in prepared
        assert "methods" in prepared
        assert "results" in prepared
        assert "conclusion" in prepared

    @pytest.mark.asyncio
    async def test_export_to_markdown(self, sample_paper_metadata):
        """Test exporting notes to Markdown."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        notes_content = "## Test Notes\n\nContent here"
        metadata = {**sample_paper_metadata, "generated_at": "2024-01-15T10:00:00Z"}

        markdown = generator.export_to_markdown(notes_content, metadata)

        # Verify header contains metadata
        assert "Deep Learning for Medical Image Analysis" in markdown
        assert "Zhang San" in markdown
        assert "2024" in markdown
        assert "Nature Medicine" in markdown
        assert "Test Notes" in markdown

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_paper_metadata, sample_imrad_structure):
        """Test error handling for LLM failures."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.side_effect = Exception("API Error: Rate limit exceeded")

            with pytest.raises(Exception) as exc_info:
                await generator.generate_notes(
                    paper_metadata=sample_paper_metadata,
                    imrad_structure=sample_imrad_structure
                )

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_environment_variable_model(self):
        """Test that LLM_MODEL environment variable is respected."""
        from app.core.notes_generator import NotesGenerator

        with patch.dict(os.environ, {"LLM_MODEL": "claude-3-haiku"}):
            generator = NotesGenerator()
            assert generator.model == "claude-3-haiku"

    @pytest.mark.asyncio
    async def test_prompt_includes_paper_info(self, sample_paper_metadata, sample_imrad_structure, mock_litellm_response):
        """Test that prompt includes paper metadata."""
        from app.core.notes_generator import NotesGenerator

        generator = NotesGenerator()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_response

            await generator.generate_notes(
                paper_metadata=sample_paper_metadata,
                imrad_structure=sample_imrad_structure
            )

            call_args = mock_acompletion.call_args
            messages = call_args.kwargs["messages"]
            prompt = messages[0]["content"]

            # Verify paper info in prompt
            assert "Deep Learning for Medical Image Analysis" in prompt
            assert "Zhang San" in prompt
            assert "2024" in prompt
            assert "Nature Medicine" in prompt

            # Verify IMRaD sections in prompt
            assert "INTRODUCTION:" in prompt
            assert "METHODS:" in prompt
            assert "RESULTS:" in prompt
            assert "CONCLUSION:" in prompt

    def test_prompt_template_structure(self):
        """Test that IMRaD prompt template has correct structure."""
        from app.core.notes_generator import IMRAD_PROMPT_TEMPLATE

        # Verify all 6 sections are in template
        assert "## 1. Research Question & Motivation" in IMRAD_PROMPT_TEMPLATE
        assert "## 2. Key Contributions & Innovation Points" in IMRAD_PROMPT_TEMPLATE
        assert "## 3. Methodology" in IMRAD_PROMPT_TEMPLATE
        assert "## 4. Main Results & Findings" in IMRAD_PROMPT_TEMPLATE
        assert "## 5. Limitations & Future Work" in IMRAD_PROMPT_TEMPLATE
        assert "## 6. Personal Takeaways" in IMRAD_PROMPT_TEMPLATE

        # Verify placeholders
        assert "{title}" in IMRAD_PROMPT_TEMPLATE
        assert "{authors}" in IMRAD_PROMPT_TEMPLATE
        assert "{year}" in IMRAD_PROMPT_TEMPLATE
        assert "{venue}" in IMRAD_PROMPT_TEMPLATE
        assert "{introduction}" in IMRAD_PROMPT_TEMPLATE
        assert "{methods}" in IMRAD_PROMPT_TEMPLATE
        assert "{results}" in IMRAD_PROMPT_TEMPLATE
        assert "{conclusion}" in IMRAD_PROMPT_TEMPLATE
        assert "{modification_request}" in IMRAD_PROMPT_TEMPLATE
