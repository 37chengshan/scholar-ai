"""Test Milvus metadata fields and quality scoring (per D-06).

Tests:
- Collection schema with 6 new metadata fields
- Field names match D-06 spec
- Field types correct (FLOAT, INT32, BOOL)
- calculate_chunk_quality() returns 0-1 range
"""

import pytest
from pymilvus import Collection, DataType
from unittest.mock import Mock, patch

from app.core.milvus_service import MilvusService

# These functions will be added in the implementation phase
# calculate_chunk_quality, is_header_footer will be standalone functions


class TestMilvusMetadataFields:
    """Test enhanced collection schema with metadata fields."""

    @pytest.fixture
    def mock_milvus_service(self):
        """Create mock MilvusService for testing."""
        service = MilvusService()
        service._connected = True
        service._alias = "test_alias"
        
        # Mock the Collection creation to avoid real Milvus connection
        with patch('app.core.milvus_service.Collection') as mock_collection_class:
            mock_collection = Mock()
            mock_collection.name = "paper_contents"
            # Return mock collection
            mock_collection_class.return_value = mock_collection
            
            # Mock the schema creation
            with patch.object(service, '_create_collection_schema') as mock_create_schema:
                # Will create schema with actual fields when method is called
                def create_schema_side_effect(name, fields):
                    mock_coll = Mock()
                    mock_coll.name = name
                    
                    # Build mock schema from actual fields passed
                    mock_schema = Mock()
                    mock_schema.fields = fields
                    mock_coll.schema = mock_schema
                    
                    return mock_coll
                    
                mock_create_schema.side_effect = create_schema_side_effect
                yield service

    def test_collection_has_6_new_fields(self, mock_milvus_service):
        """Test that collection has 6 new metadata fields per D-06."""
        # This will fail until create_paper_contents_collection() is updated
        collection = mock_milvus_service.create_paper_contents_collection()

        # Get schema
        schema = collection.schema

        # Expected new fields per D-06
        expected_new_fields = [
            "section",
            "quality_score",
            "word_count",
            "has_equations",
            "has_figures",
            "extraction_version",
        ]

        # Check all new fields exist
        field_names = [field.name for field in schema.fields]
        for expected_field in expected_new_fields:
            assert expected_field in field_names, f"Field {expected_field} not found in schema"

    def test_field_names_match_d06_spec(self, mock_milvus_service):
        """Test field names exactly match D-06 specification."""
        collection = mock_milvus_service.create_paper_contents_collection()
        schema = collection.schema

        # Expected field names per D-06 (lines 384-402 in CONTEXT.md)
        expected_fields = [
            "id",
            "paper_id",
            "user_id",
            "content_type",
            "page_num",
            "section",  # NEW
            "quality_score",  # NEW
            "word_count",  # NEW
            "has_equations",  # NEW
            "has_figures",  # NEW
            "extraction_version",  # NEW
            "content_data",
            "raw_data",
            "embedding",
        ]

        field_names = [field.name for field in schema.fields]
        assert field_names == expected_fields, f"Field names don't match D-06 spec. Got: {field_names}"

    def test_field_types_correct(self, mock_milvus_service):
        """Test field types are correct per D-06."""
        collection = mock_milvus_service.create_paper_contents_collection()
        schema = collection.schema

        # Build field type mapping
        field_types = {}
        for field in schema.fields:
            field_types[field.name] = field.dtype

        # Check new field types
        assert field_types["quality_score"] == DataType.FLOAT, "quality_score should be FLOAT"
        assert field_types["word_count"] == DataType.INT32, "word_count should be INT32"
        assert field_types["has_equations"] == DataType.BOOL, "has_equations should be BOOL"
        assert field_types["has_figures"] == DataType.BOOL, "has_figures should be BOOL"
        assert field_types["extraction_version"] == DataType.INT32, "extraction_version should be INT32"
        assert field_types["section"] == DataType.VARCHAR, "section should be VARCHAR"

    def test_collection_exists_with_schema(self, mock_milvus_service):
        """Test that collection is created and has correct schema."""
        collection = mock_milvus_service.create_paper_contents_collection()

        # Collection should exist
        assert collection is not None
        assert collection.name == "paper_contents"

        # Schema should have 14 fields total (8 old + 6 new)
        assert len(collection.schema.fields) == 14


class TestQualityScoring:
    """Test chunk quality scoring algorithm."""

    def test_calculate_chunk_quality_returns_0_to_1(self):
        """Test quality score is in 0-1 range."""
        # Import function that will be added in GREEN phase
        from app.core.milvus_service import calculate_chunk_quality

        # Test various chunk types
        test_cases = [
            {"text": "This is a normal paragraph with sufficient length.", "section": "Introduction"},
            {"text": "Short", "section": "Methods"},  # Too short
            {"text": "123", "section": "Results"},  # Header/footer
            {"text": "Full text in references section.", "section": "References"},
            {"text": "Mathematical content", "section": "Methods", "has_equations": True},
            {"text": "Figure description", "section": "Results", "has_figures": True},
        ]

        for chunk in test_cases:
            score = calculate_chunk_quality(chunk)
            assert 0.0 <= score <= 1.0, f"Quality score {score} out of range for chunk: {chunk}"

    def test_short_text_reduced_quality(self):
        """Test that very short text gets reduced quality score."""
        from app.core.milvus_service import calculate_chunk_quality

        short_chunk = {"text": "Tiny", "section": "Methods"}
        score = calculate_chunk_quality(short_chunk)

        # Short text should get 0.3 multiplier
        assert score <= 0.3, f"Short text quality {score} should be <= 0.3"

    def test_header_footer_low_quality(self):
        """Test header/footer content gets very low quality."""
        from app.core.milvus_service import calculate_chunk_quality

        header_chunk = {"text": "Page 5", "section": ""}
        score = calculate_chunk_quality(header_chunk)

        # Header/footer should get 0.2 multiplier
        assert score <= 0.2, f"Header/footer quality {score} should be <= 0.2"

    def test_references_section_reduced(self):
        """Test references section gets reduced quality."""
        from app.core.milvus_service import calculate_chunk_quality

        ref_chunk = {"text": "Smith et al. (2023). Journal Article.", "section": "References"}
        score = calculate_chunk_quality(ref_chunk)

        # References should get 0.5 multiplier
        assert score <= 0.5, f"References quality {score} should be <= 0.5"

    def test_equations_figures_boosted(self):
        """Test content with equations/figures gets quality boost."""
        from app.core.milvus_service import calculate_chunk_quality

        normal_chunk = {"text": "Normal paragraph with enough length.", "section": "Methods"}
        normal_score = calculate_chunk_quality(normal_chunk)

        equation_chunk = {"text": "Mathematical equation: E=mc^2", "section": "Methods", "has_equations": True}
        equation_score = calculate_chunk_quality(equation_chunk)

        # Equations should boost score (1.2 multiplier)
        assert equation_score >= normal_score, "Equation content should have higher quality"

        figure_chunk = {"text": "Figure shows experimental setup.", "section": "Results", "has_figures": True}
        figure_score = calculate_chunk_quality(figure_chunk)

        assert figure_score >= normal_score, "Figure content should have higher quality"

    def test_is_header_footer_detects_patterns(self):
        """Test header/footer detection patterns."""
        from app.core.milvus_service import is_header_footer

        # Should detect as header/footer
        assert is_header_footer("123") == True, "Page number detected"
        assert is_header_footer("Page 5") == True, "Page label detected"
        assert is_header_footer("第 10 页") == True, "Chinese page label detected"
        assert is_header_footer("2024-01-15") == True, "Date pattern detected"

        # Should NOT detect as header/footer
        assert is_header_footer("This is normal paragraph text.") == False
        assert is_header_footer("The experimental results show...") == False