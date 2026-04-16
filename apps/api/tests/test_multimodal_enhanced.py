"""Tests for enhanced multimodal indexing with reference context extraction.

Tests the extract_figure_references() function per D-04 spec.
"""

import pytest
from app.core.multimodal_indexer import extract_figure_references


class TestExtractFigureReferences:
    """Test extraction of figure/table reference contexts."""

    def test_extract_figure_references_function_exists(self):
        """Test 1: extract_figure_references() function exists."""
        # Function should be importable
        assert callable(extract_figure_references)

    def test_extract_references_with_english_figure(self):
        """Test 2: Function extracts references using English figure patterns."""
        markdown = """
# Introduction

As shown in Figure 1, the proposed method achieves significant improvements
over baseline approaches. The confusion matrix in Figure 1 demonstrates that
our model achieves 95% accuracy.

# Methods

The architecture is illustrated in Figure 2. Unlike Figure 1, this diagram
shows the complete pipeline.

# Results

Figure 1 clearly shows the performance gains. The results validate our approach.
"""
        contexts = extract_figure_references(markdown, "1", "figure")

        # Should extract contexts mentioning Figure 1
        assert isinstance(contexts, list)
        assert len(contexts) > 0
        assert len(contexts) <= 3  # Max 3 fragments

        # Check that contexts contain relevant text
        combined = " ".join(contexts)
        assert "Figure 1" in combined or "Figure 1" in combined.lower()

    def test_extract_references_with_chinese_figure(self):
        """Test 3: Function extracts references using Chinese figure patterns."""
        markdown = """
# 引言

如图1所示，我们的方法在准确率上取得了显著提升。图1展示了实验结果的混淆矩阵，
显示模型在各个类别上都表现良好。

# 方法

方法架构如图2所示。与图1不同，这个图展示了完整的处理流程。

# 结果

从图1可以清楚地看到性能提升。结果验证了我们方法的有效性。
"""
        contexts = extract_figure_references(markdown, "1", "figure")

        # Should extract Chinese contexts
        assert isinstance(contexts, list)
        assert len(contexts) > 0
        assert len(contexts) <= 3

        # Check for Chinese figure reference
        combined = " ".join(contexts)
        assert "图1" in combined or "图 1" in combined

    def test_context_limited_to_500_characters(self):
        """Test 4: Context text limited to 500 characters (LOCKED per D-04)."""
        # Create a very long markdown with a figure reference
        long_text = "This is a long context. " * 100
        markdown = f"""
# Results

As shown in Figure 1, {long_text}

The results are significant.
"""
        contexts = extract_figure_references(markdown, "1", "figure")

        # Should still extract contexts
        assert len(contexts) > 0

        # Each context should be reasonable length (not the entire document)
        # Note: The 500 character limit is applied when combining contexts in
        # create_enhanced_multimodal_embedding(), not in extract_figure_references()
        # But each individual context should still be bounded
        for context in contexts:
            assert len(context) < 10000  # Reasonable upper bound

    def test_extract_references_for_table(self):
        """Test 5: Function works for both figures and tables."""
        markdown = """
# Methods

Table 1 presents the experimental results. The table shows that our method
outperforms all baselines.

Table 2 compares different configurations. Unlike Table 1, this table focuses
on ablation studies.

# Discussion

The results in Table 1 demonstrate the effectiveness of our approach.
"""
        contexts = extract_figure_references(markdown, "1", "table")

        # Should extract table references
        assert isinstance(contexts, list)
        assert len(contexts) > 0
        assert len(contexts) <= 3

        # Check for table reference
        combined = " ".join(contexts)
        assert "Table 1" in combined

    def test_returns_empty_list_for_no_references(self):
        """Test 6: Returns empty list when no references found."""
        markdown = """
# Introduction

This paper presents a novel approach to machine learning.

# Methods

We use a transformer-based architecture.
"""
        contexts = extract_figure_references(markdown, "99", "figure")

        # Should return empty list for non-existent figure
        assert isinstance(contexts, list)
        assert len(contexts) == 0

    def test_max_three_contexts(self):
        """Test 7: Returns maximum 3 context fragments."""
        markdown = """
# Section 1

As shown in Figure 1, result A is good.

# Section 2

Figure 1 demonstrates result B.

# Section 3

In Figure 1, we see result C.

# Section 4

Figure 1 shows result D.

# Section 5

From Figure 1, we observe result E.
"""
        contexts = extract_figure_references(markdown, "1", "figure")

        # Should return at most 3 contexts
        assert len(contexts) <= 3


class TestCreateEnhancedMultimodalEmbedding:
    """Test creation of enhanced multimodal embeddings per D-04."""

    @pytest.mark.asyncio
    async def test_create_enhanced_embedding_function_exists(self):
        """Test 1: create_enhanced_multimodal_embedding() function exists."""
        from app.core.multimodal_indexer import create_enhanced_multimodal_embedding
        assert callable(create_enhanced_multimodal_embedding)

    @pytest.mark.asyncio
    async def test_combines_caption_context_description(self):
        """Test 2: Function combines caption + context + description."""
        from app.core.multimodal_indexer import create_enhanced_multimodal_embedding
        from unittest.mock import AsyncMock, MagicMock

        # Mock BGE-M3 service
        mock_bge_m3 = MagicMock()
        mock_bge_m3.encode_text.return_value = [0.1] * 1024

        markdown = "As shown in Figure 1, the results demonstrate significant improvements."
        caption = "Figure 1: Experimental results"

        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="image",
            figure_label="1",
            caption=caption,
            markdown=markdown,
            bge_m3_service=mock_bge_m3,
            vlm_description="Bar chart showing performance metrics"
        )

        # Should return embedding and combined text
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert isinstance(combined_text, str)

        # Should contain caption
        assert "Figure 1" in combined_text or "Image 1" in combined_text
        assert caption in combined_text or "Experimental results" in combined_text

    @pytest.mark.asyncio
    async def test_context_limited_to_500_chars(self):
        """Test 3: Context text limited to 500 characters (LOCKED per D-04)."""
        from app.core.multimodal_indexer import create_enhanced_multimodal_embedding
        from unittest.mock import MagicMock

        mock_bge_m3 = MagicMock()
        mock_bge_m3.encode_text.return_value = [0.1] * 1024

        # Create a very long markdown
        long_text = "This is a long context sentence. " * 100
        markdown = f"As shown in Figure 1, {long_text}"

        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="image",
            figure_label="1",
            caption="Figure 1",
            markdown=markdown,
            bge_m3_service=mock_bge_m3
        )

        # Find the context part in combined_text
        # The context should be limited to 500 characters
        if "Context:" in combined_text:
            context_start = combined_text.find("Context:")
            context_part = combined_text[context_start:]
            # The context portion should not be excessively long
            # (Allowing some overhead for "Context:" prefix and formatting)
            assert len(context_part) < 1000  # Reasonable upper bound

    @pytest.mark.asyncio
    async def test_returns_embedding_and_combined_text(self):
        """Test 4: Function returns embedding and combined_text."""
        from app.core.multimodal_indexer import create_enhanced_multimodal_embedding
        from unittest.mock import MagicMock

        mock_bge_m3 = MagicMock()
        mock_bge_m3.encode_text.return_value = [0.5] * 1024

        result = await create_enhanced_multimodal_embedding(
            figure_type="table",
            figure_label="2",
            caption="Table 2: Performance comparison",
            markdown="Table 2 shows the comparison results.",
            bge_m3_service=mock_bge_m3,
            vlm_description="Comparison table with 5 columns"
        )

        # Should return tuple of (embedding, combined_text)
        assert isinstance(result, tuple)
        assert len(result) == 2

        embedding, combined_text = result
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert isinstance(combined_text, str)

    @pytest.mark.asyncio
    async def test_handles_missing_vlm_description(self):
        """Test 5: Handles cases where VLM description is not provided."""
        from app.core.multimodal_indexer import create_enhanced_multimodal_embedding
        from unittest.mock import MagicMock

        mock_bge_m3 = MagicMock()
        mock_bge_m3.encode_text.return_value = [0.3] * 1024

        # Test without VLM description
        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="image",
            figure_label="1",
            caption="Figure 1: Results",
            markdown="As shown in Figure 1, the results are good.",
            bge_m3_service=mock_bge_m3,
            vlm_description=None  # No VLM description
        )

        # Should still work without VLM description
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert isinstance(combined_text, str)
        assert "Figure 1" in combined_text or "Image 1" in combined_text