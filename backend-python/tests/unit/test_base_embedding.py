"""Tests for BaseEmbeddingService abstract interface.

Tests verify:
- Abstract interface design per D-01, D-02
- Required method signatures
- Cannot be instantiated directly (ABC)
- Supports both text-only and multimodal implementations
"""

import pytest
from abc import ABC
from typing import List, Dict, Any
from PIL import Image

from app.core.embedding.base import BaseEmbeddingService


class TestBaseEmbeddingServiceInterface:
    """Test abstract interface contract."""

    def test_base_embedding_is_abstract(self):
        """BaseEmbeddingService should be abstract (cannot instantiate directly)."""
        # Should raise TypeError when trying to instantiate abstract class
        with pytest.raises(TypeError) as exc_info:
            BaseEmbeddingService()
        
        # Error should mention abstract methods
        assert "abstract" in str(exc_info.value).lower()

    def test_has_encode_text_method(self):
        """BaseEmbeddingService should define encode_text() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'encode_text')
        
        # Check it's abstract
        encode_text = getattr(BaseEmbeddingService, 'encode_text')
        assert hasattr(encode_text, '__isabstractmethod__')
        assert encode_text.__isabstractmethod__ is True

    def test_has_encode_image_method(self):
        """BaseEmbeddingService should define encode_image() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'encode_image')
        
        # Check it's abstract
        encode_image = getattr(BaseEmbeddingService, 'encode_image')
        assert hasattr(encode_image, '__isabstractmethod__')
        assert encode_image.__isabstractmethod__ is True

    def test_has_encode_table_method(self):
        """BaseEmbeddingService should define encode_table() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'encode_table')
        
        # Check it's abstract
        encode_table = getattr(BaseEmbeddingService, 'encode_table')
        assert hasattr(encode_table, '__isabstractmethod__')
        assert encode_table.__isabstractmethod__ is True

    def test_has_load_model_method(self):
        """BaseEmbeddingService should define load_model() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'load_model')
        
        # Check it's abstract
        load_model = getattr(BaseEmbeddingService, 'load_model')
        assert hasattr(load_model, '__isabstractmethod__')
        assert load_model.__isabstractmethod__ is True

    def test_has_is_loaded_method(self):
        """BaseEmbeddingService should define is_loaded() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'is_loaded')
        
        # Check it's abstract
        is_loaded = getattr(BaseEmbeddingService, 'is_loaded')
        assert hasattr(is_loaded, '__isabstractmethod__')
        assert is_loaded.__isabstractmethod__ is True

    def test_has_get_model_info_method(self):
        """BaseEmbeddingService should define get_model_info() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'get_model_info')
        
        # Check it's abstract
        get_model_info = getattr(BaseEmbeddingService, 'get_model_info')
        assert hasattr(get_model_info, '__isabstractmethod__')
        assert get_model_info.__isabstractmethod__ is True

    def test_has_supports_multimodal_method(self):
        """BaseEmbeddingService should define supports_multimodal() abstract method."""
        # Check method exists
        assert hasattr(BaseEmbeddingService, 'supports_multimodal')
        
        # Check it's abstract
        supports_multimodal = getattr(BaseEmbeddingService, 'supports_multimodal')
        assert hasattr(supports_multimodal, '__isabstractmethod__')
        assert supports_multimodal.__isabstractmethod__ is True


class TestConcreteImplementation:
    """Test that concrete implementations must implement all methods."""

    def test_partial_implementation_fails(self):
        """Partial implementation should fail to instantiate."""
        # Create incomplete implementation
        class IncompleteEmbedding(BaseEmbeddingService):
            def encode_text(self, text):
                return [0.0] * 2048
            
            # Missing other abstract methods
        
        # Should raise TypeError
        with pytest.raises(TypeError) as exc_info:
            IncompleteEmbedding()
        
        # Error should mention missing abstract methods
        assert "abstract" in str(exc_info.value).lower()

    def test_full_implementation_succeeds(self):
        """Full implementation should instantiate successfully."""
        # Create complete implementation
        class MockEmbeddingService(BaseEmbeddingService):
            def load_model(self) -> None:
                self._loaded = True
            
            def encode_text(self, text):
                return [0.1] * 2048
            
            def encode_image(self, image):
                return [0.2] * 2048
            
            def encode_table(self, caption="", headers=[], rows=[]):
                return [0.3] * 2048
            
            def is_loaded(self) -> bool:
                return self._loaded
            
            def get_model_info(self) -> Dict[str, str]:
                return {"name": "mock", "version": "1.0", "type": "multimodal"}
            
            def supports_multimodal(self) -> bool:
                return True
        
        # Should instantiate without error
        service = MockEmbeddingService()
        assert service is not None
        assert isinstance(service, BaseEmbeddingService)
        assert isinstance(service, ABC)


class TestMethodSignatures:
    """Test method signatures match interface design."""

    def test_encode_text_signature(self):
        """encode_text() should accept Union[str, List[str]]."""
        # Check method signature via __init__ (if available)
        # We'll test this with concrete implementation in integration tests
        pass  # Signature check in concrete tests

    def test_encode_image_signature(self):
        """encode_image() should accept Union[str, Image.Image, List[Image.Image]]."""
        pass  # Signature check in concrete tests

    def test_encode_table_signature(self):
        """encode_table() should accept caption, headers, rows parameters."""
        # Test with complete implementation
        class MockEmbedding(BaseEmbeddingService):
            def load_model(self) -> None:
                pass
            
            def encode_text(self, text):
                return []
            
            def encode_image(self, image):
                return []
            
            def encode_table(self, caption="", headers=[], rows=[]):
                # Verify parameters are accepted
                assert isinstance(caption, str)
                assert isinstance(headers, list)
                assert isinstance(rows, list)
                return [0.0] * 2048
            
            def is_loaded(self) -> bool:
                return True
            
            def get_model_info(self) -> Dict[str, str]:
                return {}
            
            def supports_multimodal(self) -> bool:
                return True
        
        service = MockEmbedding()
        # Call with default parameters
        result = service.encode_table()
        assert len(result) == 2048
        
        # Call with custom parameters
        result = service.encode_table(
            caption="Test Table",
            headers=["Col1", "Col2"],
            rows=[{"Col1": "Val1", "Col2": "Val2"}]
        )
        assert len(result) == 2048

    def test_is_loaded_returns_bool(self):
        """is_loaded() should return bool."""
        class MockEmbedding(BaseEmbeddingService):
            def load_model(self) -> None:
                self._loaded = True
            
            def encode_text(self, text):
                return []
            
            def encode_image(self, image):
                return []
            
            def encode_table(self, caption="", headers=[], rows=[]):
                return []
            
            def is_loaded(self) -> bool:
                return self._loaded
            
            def get_model_info(self) -> Dict[str, str]:
                return {}
            
            def supports_multimodal(self) -> bool:
                return True
        
        service = MockEmbedding()
        service.load_model()
        assert service.is_loaded() is True
        assert isinstance(service.is_loaded(), bool)

    def test_get_model_info_returns_dict(self):
        """get_model_info() should return Dict[str, str]."""
        class MockEmbedding(BaseEmbeddingService):
            def load_model(self) -> None:
                pass
            
            def encode_text(self, text):
                return []
            
            def encode_image(self, image):
                return []
            
            def encode_table(self, caption="", headers=[], rows=[]):
                return []
            
            def is_loaded(self) -> bool:
                return True
            
            def get_model_info(self) -> Dict[str, str]:
                return {
                    "name": "mock-embedding",
                    "version": "1.0",
                    "type": "text-only"
                }
            
            def supports_multimodal(self) -> bool:
                return False
        
        service = MockEmbedding()
        info = service.get_model_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "type" in info

    def test_supports_multimodal_returns_bool(self):
        """supports_multimodal() should return bool."""
        class MockEmbedding(BaseEmbeddingService):
            def load_model(self) -> None:
                pass
            
            def encode_text(self, text):
                return []
            
            def encode_image(self, image):
                return []
            
            def encode_table(self, caption="", headers=[], rows=[]):
                return []
            
            def is_loaded(self) -> bool:
                return True
            
            def get_model_info(self) -> Dict[str, str]:
                return {}
            
            def supports_multimodal(self) -> bool:
                return False
        
        service = MockEmbedding()
        assert service.supports_multimodal() is False
        assert isinstance(service.supports_multimodal(), bool)


class TestInheritanceStructure:
    """Test inheritance and ABC compliance."""

    def test_inherits_from_abc(self):
        """BaseEmbeddingService should inherit from ABC."""
        assert issubclass(BaseEmbeddingService, ABC)

    def test_is_abstract_base_class(self):
        """BaseEmbeddingService should be an abstract base class."""
        # ABCMeta should be the metaclass
        from abc import ABCMeta
        assert type(BaseEmbeddingService) is ABCMeta