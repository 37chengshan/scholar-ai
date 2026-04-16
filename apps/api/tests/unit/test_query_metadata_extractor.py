"""Unit tests for query metadata extraction.

Tests metadata filter extraction from user queries:
- Year range extraction (2023年, 2020-2023, 最近3年)
- Author extraction (张三的研究, LeCun的论文)
- Keyword extraction (关于注意力机制的)
- Combined metadata filters
"""

import pytest
from datetime import datetime
from app.core.query_metadata_extractor import (
    extract_year_range,
    extract_author,
    extract_keywords,
    extract_metadata_filters,
)


class TestYearRangeExtraction:
    """Test year range extraction from queries."""

    def test_single_year_extraction(self):
        """Test 1: extract_year_range('2023年的论文') returns (2023, 2023)"""
        query = "2023年的论文"
        year_range = extract_year_range(query)
        assert year_range == (2023, 2023)

    def test_year_range_extraction(self):
        """Test 2: extract_year_range('2020-2023') returns (2020, 2023)"""
        query = "2020-2023"
        year_range = extract_year_range(query)
        assert year_range == (2020, 2023)

    def test_relative_year_extraction(self):
        """Test 3: extract_year_range('最近3年') returns dynamic range"""
        query = "最近3年"
        year_range = extract_year_range(query)
        current_year = datetime.now().year
        expected_start = current_year - 3
        assert year_range == (expected_start, current_year)

    def test_no_year_extraction(self):
        """extract_year_range returns None when no year pattern found"""
        query = "深度学习论文"
        year_range = extract_year_range(query)
        assert year_range is None

    def test_year_extraction_various_formats(self):
        """Test various year formats"""
        assert extract_year_range("2022年发表的") == (2022, 2022)
        assert extract_year_range("2018-2022期间") == (2018, 2022)
        assert extract_year_range("最近5年的研究") == (datetime.now().year - 5, datetime.now().year)


class TestAuthorExtraction:
    """Test author extraction from queries."""

    def test_chinese_author_extraction(self):
        """Test 4: extract_author('张三的研究') returns '张三'"""
        query = "张三的研究"
        author = extract_author(query)
        assert author == "张三"

    def test_english_author_extraction(self):
        """Test 5: extract_author('LeCun的论文') returns 'LeCun'"""
        query = "LeCun的论文"
        author = extract_author(query)
        assert author == "LeCun"

    def test_author_with_author_keyword(self):
        """Test author extraction with 'author:' keyword"""
        query = "author: Hinton"
        author = extract_author(query)
        assert author == "Hinton"

    def test_no_author_extraction(self):
        """extract_author returns None when no author pattern found"""
        query = "目标检测综述"
        author = extract_author(query)
        assert author is None

    def test_author_extraction_various_patterns(self):
        """Test various author patterns"""
        assert extract_author("王五的论文") == "王五"
        assert extract_author("author:Krizhevsky") == "Krizhevsky"


class TestKeywordExtraction:
    """Test keyword extraction from queries."""

    def test_keyword_extraction_with_about(self):
        """Test 6: extract_keywords('关于注意力机制的') returns '注意力机制'"""
        query = "关于注意力机制的"
        keywords = extract_keywords(query)
        assert keywords == "注意力机制"

    def test_keyword_extraction_with_related(self):
        """Test keyword extraction with '相关' suffix"""
        query = "深度学习相关"
        keywords = extract_keywords(query)
        assert keywords == "深度学习"

    def test_no_keyword_extraction(self):
        """extract_keywords returns None when no keyword pattern found"""
        query = "ResNet论文"
        keywords = extract_keywords(query)
        assert keywords is None

    def test_keyword_extraction_various_patterns(self):
        """Test various keyword patterns"""
        assert extract_keywords("关于YOLO的") == "YOLO"
        assert extract_keywords("NLP相关论文") == "NLP"


class TestMetadataFiltersExtraction:
    """Test combined metadata filter extraction."""

    def test_combined_filters_extraction(self):
        """Test 7: extract_metadata_filters combines all filters correctly"""
        query = "2023年张三的关于注意力机制的论文"
        filters = extract_metadata_filters(query)

        assert "year_range" in filters
        assert filters["year_range"] == (2023, 2023)

        assert "author" in filters
        assert filters["author"] == "张三"

        assert "keywords" in filters
        assert filters["keywords"] == "注意力机制"

    def test_partial_filters_extraction(self):
        """Test extraction with only some filters present"""
        query = "2020-2023期间的YOLO论文"
        filters = extract_metadata_filters(query)

        assert "year_range" in filters
        assert filters["year_range"] == (2020, 2023)

        # No author or keywords
        assert "author" not in filters
        assert "keywords" not in filters

    def test_no_filters_extraction(self):
        """Test extraction when no filters present"""
        query = "深度学习方法"
        filters = extract_metadata_filters(query)
        assert filters == {}

    def test_filters_return_types(self):
        """Test that filters return correct types"""
        query = "最近2年张三的论文"
        filters = extract_metadata_filters(query)

        # year_range should be tuple of ints
        if "year_range" in filters:
            assert isinstance(filters["year_range"], tuple)
            assert len(filters["year_range"]) == 2
            assert isinstance(filters["year_range"][0], int)
            assert isinstance(filters["year_range"][1], int)

        # author should be str
        if "author" in filters:
            assert isinstance(filters["author"], str)

        # keywords should be str
        if "keywords" in filters:
            assert isinstance(filters["keywords"], str)

    def test_multiple_patterns_in_one_query(self):
        """Test extraction with multiple patterns"""
        query = "author:LeCun 2022年关于CNN的研究"
        filters = extract_metadata_filters(query)

        assert filters["author"] == "LeCun"
        assert filters["year_range"] == (2022, 2022)
        assert filters["keywords"] == "CNN"