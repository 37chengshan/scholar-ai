"""Unit tests for modality fusion module.

Tests:
- detect_intent: Query intent detection
- weighted_rrf_fusion: Weighted RRF fusion algorithm
- WEIGHT_PRESETS: Weight configurations
"""

import pytest
from app.core.modality_fusion import (
    detect_intent,
    weighted_rrf_fusion,
    IMAGE_KEYWORDS,
    TABLE_KEYWORDS,
    WEIGHT_PRESETS,
)


class TestDetectIntent:
    """Tests for intent detection function."""

    def test_detect_intent_image_keywords(self):
        """Test that image keywords trigger image_weighted intent."""
        # Test various image keywords
        assert detect_intent("show me the figure") == "image_weighted"
        assert detect_intent("display the 图表") == "image_weighted"
        assert detect_intent("chart showing results") == "image_weighted"
        assert detect_intent("图像 analysis") == "image_weighted"
        assert detect_intent("示意图 of system") == "image_weighted"
        assert detect_intent("流程图 diagram") == "image_weighted"

    def test_detect_intent_table_keywords(self):
        """Test that table keywords trigger table_weighted intent."""
        # Test various table keywords
        assert detect_intent("performance table") == "table_weighted"
        assert detect_intent("表格 comparison") == "table_weighted"
        assert detect_intent("数据 analysis") == "table_weighted"
        assert detect_intent("对比 results") == "table_weighted"
        assert detect_intent("性能指标 table") == "table_weighted"
        assert detect_intent("实验结果 table") == "table_weighted"

    def test_detect_intent_default(self):
        """Test that queries without keywords return default intent."""
        assert detect_intent("YOLO architecture") == "default"
        assert detect_intent("neural network layers") == "default"
        assert detect_intent("loss function") == "default"
        assert detect_intent("training procedure") == "default"

    def test_detect_intent_case_insensitive(self):
        """Test that intent detection is case-insensitive."""
        assert detect_intent("FIGURE showing results") == "image_weighted"
        assert detect_intent("TABLE with data") == "table_weighted"
        assert detect_intent("Show Me The CHART") == "image_weighted"


class TestWeightedRRFFusion:
    """Tests for weighted RRF fusion function."""

    def test_weighted_rrf_fusion_basic(self):
        """Test basic RRF fusion with weights."""
        # Mock multimodal results
        multimodal_results = {
            "text": [
                {"id": "t1", "paper_id": "p1", "page_num": 1, "content_data": "text content 1"},
                {"id": "t2", "paper_id": "p1", "page_num": 2, "content_data": "text content 2"},
            ],
            "image": [
                {"id": "i1", "paper_id": "p1", "page_num": 1, "content_data": "image content 1"},
            ],
            "table": [
                {"id": "tb1", "paper_id": "p1", "page_num": 3, "content_data": "table content 1"},
            ],
        }

        weights = {"text": 0.5, "image": 0.3, "table": 0.2}

        fused = weighted_rrf_fusion(multimodal_results, weights, k=60)

        # Should return sorted results
        assert len(fused) == 4
        assert all("rrf_score" in r for r in fused)
        assert all("modality_ranks" in r for r in fused)

        # Results should be sorted by rrf_score descending
        scores = [r["rrf_score"] for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_weighted_rrf_fusion_same_item_multiple_modalities(self):
        """Test that same item appearing in multiple modalities gets combined score."""
        # Same page_num appears in text and image
        multimodal_results = {
            "text": [
                {"id": "same", "paper_id": "p1", "page_num": 1, "content_data": "content"},
            ],
            "image": [
                {"id": "same", "paper_id": "p1", "page_num": 1, "content_data": "content"},
            ],
            "table": [],
        }

        weights = {"text": 0.5, "image": 0.3, "table": 0.2}

        fused = weighted_rrf_fusion(multimodal_results, weights, k=60)

        # Should have only 1 unique result (same id/paper/page)
        assert len(fused) == 1

        # Score should combine both modalities
        result = fused[0]
        assert result["rrf_score"] > 0
        assert "text" in result["modality_ranks"]
        assert "image" in result["modality_ranks"]

    def test_weighted_rrf_fusion_empty_results(self):
        """Test fusion with empty results."""
        multimodal_results = {
            "text": [],
            "image": [],
            "table": [],
        }

        weights = {"text": 0.5, "image": 0.3, "table": 0.2}

        fused = weighted_rrf_fusion(multimodal_results, weights, k=60)

        assert fused == []

    def test_weighted_rrf_fusion_partial_results(self):
        """Test fusion with only some modalities having results."""
        multimodal_results = {
            "text": [
                {"id": "t1", "paper_id": "p1", "page_num": 1, "content_data": "text"},
            ],
            "image": [],  # No image results
            "table": [],  # No table results
        }

        weights = {"text": 0.5, "image": 0.3, "table": 0.2}

        fused = weighted_rrf_fusion(multimodal_results, weights, k=60)

        assert len(fused) == 1
        assert fused[0]["modality_ranks"]["text"] == 1


class TestWeightPresets:
    """Tests for weight preset configurations."""

    def test_weight_presets_exist(self):
        """Test that all weight presets exist."""
        assert "default" in WEIGHT_PRESETS
        assert "image_weighted" in WEIGHT_PRESETS
        assert "table_weighted" in WEIGHT_PRESETS

    def test_weight_presets_values(self):
        """Test that weight presets have correct values."""
        # Default weights
        default = WEIGHT_PRESETS["default"]
        assert default["text"] == 0.5
        assert default["image"] == 0.3
        assert default["table"] == 0.2

        # Image weights
        image_weighted = WEIGHT_PRESETS["image_weighted"]
        assert image_weighted["text"] == 0.3
        assert image_weighted["image"] == 0.6
        assert image_weighted["table"] == 0.1

        # Table weights
        table_weighted = WEIGHT_PRESETS["table_weighted"]
        assert table_weighted["text"] == 0.4
        assert table_weighted["table"] == 0.5
        assert table_weighted["image"] == 0.1

    def test_weight_presets_sum_to_one(self):
        """Test that weights in each preset sum to approximately 1.0."""
        for preset_name, preset in WEIGHT_PRESETS.items():
            total = preset["text"] + preset["image"] + preset["table"]
            assert abs(total - 1.0) < 0.01, f"{preset_name} weights sum to {total}, expected 1.0"


class TestKeywordLists:
    """Tests for keyword list configurations."""

    def test_image_keywords_exist(self):
        """Test that image keywords list exists."""
        assert len(IMAGE_KEYWORDS) > 0
        assert "figure" in IMAGE_KEYWORDS
        assert "图表" in IMAGE_KEYWORDS
        assert "chart" in IMAGE_KEYWORDS

    def test_table_keywords_exist(self):
        """Test that table keywords list exists."""
        assert len(TABLE_KEYWORDS) > 0
        assert "table" in TABLE_KEYWORDS
        assert "表格" in TABLE_KEYWORDS
        assert "数据" in TABLE_KEYWORDS

    def test_exact_keywords_match_plan(self):
        """Test that keywords match exact values from plan."""
        # IMAGE_KEYWORDS exact values from plan
        expected_image = ["图表", "figure", "chart", "图像", "示意图", "流程图", "diagram"]
        assert IMAGE_KEYWORDS == expected_image

        # TABLE_KEYWORDS exact values from plan
        expected_table = ["表格", "table", "数据", "对比", "性能指标", "实验结果"]
        assert TABLE_KEYWORDS == expected_table