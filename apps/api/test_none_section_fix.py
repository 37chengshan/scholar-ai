"""Test to verify None section handling fix."""

import pytest
from app.core.milvus_service import calculate_chunk_quality


def test_calculate_chunk_quality_with_none_section():
    """Test that calculate_chunk_quality handles None section gracefully."""
    
    # Test 1: Section is None
    chunk_none = {
        "text": "This is a test chunk",
        "section": None
    }
    score_none = calculate_chunk_quality(chunk_none)
    assert isinstance(score_none, float)
    assert 0.0 <= score_none <= 1.0
    print(f"✓ Section None handled: score={score_none}")
    
    # Test 2: Section is missing
    chunk_missing = {
        "text": "This is a test chunk"
    }
    score_missing = calculate_chunk_quality(chunk_missing)
    assert isinstance(score_missing, float)
    assert 0.0 <= score_missing <= 1.0
    print(f"✓ Section missing handled: score={score_missing}")
    
    # Test 3: Section is empty string
    chunk_empty = {
        "text": "This is a test chunk",
        "section": ""
    }
    score_empty = calculate_chunk_quality(chunk_empty)
    assert isinstance(score_empty, float)
    assert 0.0 <= score_empty <= 1.0
    print(f"✓ Section empty handled: score={score_empty}")
    
    # Test 4: Section is valid string
    chunk_valid = {
        "text": "This is a test chunk",
        "section": "introduction"
    }
    score_valid = calculate_chunk_quality(chunk_valid)
    assert isinstance(score_valid, float)
    assert 0.0 <= score_valid <= 1.0
    print(f"✓ Section valid handled: score={score_valid}")
    
    # Test 5: Section is "references"
    chunk_references = {
        "text": "This is a test chunk",
        "section": "references"
    }
    score_references = calculate_chunk_quality(chunk_references)
    assert isinstance(score_references, float)
    assert 0.0 <= score_references <= 1.0
    # References should have lower score due to quality penalty
    assert score_references < score_valid
    print(f"✓ Section references handled with penalty: score={score_references}")
    
    print("\n✅ All None section handling tests passed!")


if __name__ == "__main__":
    test_calculate_chunk_quality_with_none_section()