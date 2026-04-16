"""Unit tests for synonym expansion service.

Tests query expansion with academic synonyms:
- Synonym lookup from dictionary
- OR prefix for expanded terms
- Chinese tokenization with jieba
- Limit to top 2 synonyms per word
"""

import pytest
from app.core.synonyms import SYNONYMS, expand_query


class TestSynonymExpansion:
    """Test synonym expansion functionality."""

    def test_yolo_synonym_expansion(self):
        """Test 1: expand_query('YOLO目标检测') includes 'object detection' synonym"""
        query = "YOLO目标检测"
        expanded = expand_query(query)
        assert "object detection" in expanded
        assert "YOLO" in expanded

    def test_cnn_synonym_expansion(self):
        """Test 2: expand_query('CNN架构') includes 'convolutional neural network'"""
        query = "CNN架构"
        expanded = expand_query(query)
        assert "convolutional neural network" in expanded
        assert "CNN" in expanded

    def test_or_prefix_for_synonyms(self):
        """Test 3: Multiple synonyms added with OR prefix"""
        query = "YOLO目标检测"
        expanded = expand_query(query)
        # Should have "OR object detection" or "OR real-time detection"
        assert "OR" in expanded

    def test_non_synonym_words_preserved(self):
        """Test 4: Non-synonym words preserved unchanged"""
        query = "深度学习方法"
        expanded = expand_query(query)
        # '方法' is not in SYNONYMS, should be preserved
        assert "方法" in expanded

    def test_chinese_tokenization(self):
        """Test 5: Chinese tokenization works with jieba"""
        query = "YOLO目标检测"
        expanded = expand_query(query)
        # Should tokenize properly
        assert len(expanded) > len(query)  # Expanded should be longer

    def test_top_two_synonyms_limit(self):
        """Test 6: Limit to top 2 synonyms per word (per D-06)"""
        query = "YOLO目标检测"
        expanded = expand_query(query)
        # YOLO has 3 synonyms: ["object detection", "real-time detection", "You Only Look Once"]
        # Should only include first 2
        yolo_synonyms_in_expanded = [
            syn for syn in ["object detection", "real-time detection", "You Only Look Once"]
            if syn in expanded
        ]
        assert len(yolo_synonyms_in_expanded) <= 2

    def test_synonyms_dict_structure(self):
        """Test 7: SYNONYMS dict structure matches D-05 specification"""
        # Should have key academic terms
        assert "YOLO" in SYNONYMS
        assert "CNN" in SYNONYMS
        assert "NLP" in SYNONYMS
        assert "CV" in SYNONYMS

        # Each synonym should be a list
        assert isinstance(SYNONYMS["YOLO"], list)
        assert len(SYNONYMS["YOLO"]) > 0

        # Should have both English and Chinese terms
        assert any("目标" in key or "检测" in key for key in SYNONYMS.keys())


class TestSynonymsDictionary:
    """Test SYNONYMS dictionary completeness."""

    def test_has_object_detection_terms(self):
        """SYNONYMS should have object detection terms"""
        assert "YOLO" in SYNONYMS
        assert "目标检测" in SYNONYMS or "目标识别" in SYNONYMS

    def test_has_network_architecture_terms(self):
        """SYNONYMS should have network architecture terms"""
        assert "CNN" in SYNONYMS
        assert "RNN" in SYNONYMS or "Transformer" in SYNONYMS

    def test_has_task_terms(self):
        """SYNONYMS should have task terms (NLP/CV)"""
        assert "NLP" in SYNONYMS
        assert "CV" in SYNONYMS

    def test_has_attention_mechanism(self):
        """SYNONYMS should have attention mechanism terms"""
        assert "attention" in SYNONYMS or "注意力" in SYNONYMS

    def test_synonym_values_are_lists(self):
        """All synonym values should be lists"""
        for key, value in SYNONYMS.items():
            assert isinstance(value, list), f"{key} should have list of synonyms"

    def test_synonym_lists_have_values(self):
        """All synonym lists should have at least one value"""
        for key, value in SYNONYMS.items():
            assert len(value) > 0, f"{key} should have at least one synonym"