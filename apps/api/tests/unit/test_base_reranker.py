"""Tests for BaseRerankerService abstract interface.

Tests verify:
- Abstract methods are defined
- Interface contract is enforced
- Cannot instantiate abstract class directly
"""

import pytest
from abc import ABC
from typing import List, Dict, Any


def test_base_reranker_is_abstract():
    """Test that BaseRerankerService is an abstract class."""
    from app.core.reranker.base import BaseRerankerService

    # Should be abstract
    assert ABC in BaseRerankerService.__mro__


def test_base_reranker_has_rerank_method():
    """Test that BaseRerankerService defines rerank abstract method."""
    from app.core.reranker.base import BaseRerankerService

    # Check method exists
    assert hasattr(BaseRerankerService, 'rerank')

    # Check it's abstract
    assert getattr(BaseRerankerService.rerank, '__isabstractmethod__', False)


def test_base_reranker_has_supports_multimodal_method():
    """Test that BaseRerankerService defines supports_multimodal abstract method."""
    from app.core.reranker.base import BaseRerankerService

    # Check method exists
    assert hasattr(BaseRerankerService, 'supports_multimodal')

    # Check it's abstract
    assert getattr(BaseRerankerService.supports_multimodal, '__isabstractmethod__', False)


def test_base_reranker_has_load_model_method():
    """Test that BaseRerankerService defines load_model abstract method."""
    from app.core.reranker.base import BaseRerankerService

    # Check method exists
    assert hasattr(BaseRerankerService, 'load_model')

    # Check it's abstract
    assert getattr(BaseRerankerService.load_model, '__isabstractmethod__', False)


def test_base_reranker_has_is_loaded_method():
    """Test that BaseRerankerService defines is_loaded abstract method."""
    from app.core.reranker.base import BaseRerankerService

    # Check method exists
    assert hasattr(BaseRerankerService, 'is_loaded')

    # Check it's abstract
    assert getattr(BaseRerankerService.is_loaded, '__isabstractmethod__', False)


def test_base_reranker_has_get_model_info_method():
    """Test that BaseRerankerService defines get_model_info abstract method."""
    from app.core.reranker.base import BaseRerankerService

    # Check method exists
    assert hasattr(BaseRerankerService, 'get_model_info')

    # Check it's abstract
    assert getattr(BaseRerankerService.get_model_info, '__isabstractmethod__', False)


def test_cannot_instantiate_abstract_class():
    """Test that BaseRerankerService cannot be instantiated directly."""
    from app.core.reranker.base import BaseRerankerService

    # Should raise TypeError when trying to instantiate
    with pytest.raises(TypeError) as exc_info:
        BaseRerankerService()

    # Error message should mention abstract methods
    assert "abstract" in str(exc_info.value).lower()


def test_rerank_signature_accepts_multimodal():
    """Test that rerank() accepts both string and dict inputs for query/documents."""
    from app.core.reranker.base import BaseRerankerService
    import inspect

    # Get method signature
    sig = inspect.signature(BaseRerankerService.rerank)

    # Check parameters
    params = sig.parameters

    # Should have query, documents, top_k parameters
    assert 'query' in params
    assert 'documents' in params
    assert 'top_k' in params

    # top_k should have default value
    assert params['top_k'].default == 10


def test_rerank_return_type():
    """Test that rerank() returns List[Dict[str, Any]]."""
    from app.core.reranker.base import BaseRerankerService
    import inspect
    from typing import get_type_hints

    # Get type hints
    hints = get_type_hints(BaseRerankerService.rerank)

    # Should return List[Dict[str, Any]]
    assert 'return' in hints