"""Tests for Qwen3VLRerankerService adapter.

Tests verify:
- Implements BaseRerankerService interface
- Supports multimodal inputs (supports_multimodal=True)
- Works with text-only inputs
- Works with multimodal inputs (text + image)
- Uses local model path ./Qwen3-VL-Reranker-2B
- FP16 quantization support
- Returns structured results
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
from PIL import Image


class TestQwen3VLRerankerService:
    """Tests for Qwen3VLRerankerService adapter."""

    def test_qwen3vl_reranker_implements_base_interface(self):
        """Test that Qwen3VLRerankerService implements BaseRerankerService."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService
        from app.core.reranker.base import BaseRerankerService

        service = Qwen3VLRerankerService()

        # Should be instance of BaseRerankerService
        assert isinstance(service, BaseRerankerService)

    def test_qwen3vl_reranker_supports_multimodal_returns_true(self):
        """Test that Qwen3VLRerankerService.supports_multimodal() returns True."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        service = Qwen3VLRerankerService()

        # Should return True (multimodal)
        assert service.supports_multimodal() is True

    def test_qwen3vl_reranker_is_loaded_initially_false(self):
        """Test that Qwen3VLRerankerService.is_loaded() returns False before load_model()."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        service = Qwen3VLRerankerService()

        # Should return False initially
        assert service.is_loaded() is False

    def test_qwen3vl_reranker_get_model_info(self):
        """Test that Qwen3VLRerankerService.get_model_info() returns correct info."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        service = Qwen3VLRerankerService()

        info = service.get_model_info()

        # Should return dict with required keys
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "type" in info

        # Should indicate multimodal
        assert info["type"] == "multimodal"
        assert "qwen" in info["name"].lower()

    def test_qwen3vl_reranker_local_model_path(self):
        """Test that Qwen3VLRerankerService uses local model path."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        service = Qwen3VLRerankerService()

        # Should use local path ./Qwen3-VL-Reranker-2B
        assert "Qwen3-VL-Reranker-2B" in service.MODEL_PATH

    def test_qwen3vl_reranker_quantization_config(self):
        """Test that Qwen3VLRerankerService has quantization config."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Test FP16 quantization
        service_fp16 = Qwen3VLRerankerService(quantization="fp16")
        assert service_fp16.quantization == "fp16"

        # Test INT8 quantization
        service_int8 = Qwen3VLRerankerService(quantization="int8")
        assert service_int8.quantization == "int8"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_load_model_fp16(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService.load_model() loads model with FP16."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService
        import torch

        service = Qwen3VLRerankerService(quantization="fp16")

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        # Load model
        service.load_model()

        # Should set initialized flag
        assert service.is_loaded() is True

        # Should have called from_pretrained
        mock_model_from_pretrained.assert_called_once()
        
        # Check kwargs for FP16
        call_kwargs = mock_model_from_pretrained.call_args[1]
        assert call_kwargs.get("torch_dtype") == torch.float16

    def test_qwen3vl_reranker_rerank_before_load_raises(self):
        """Test that rerank() before load_model() raises RuntimeError."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        service = Qwen3VLRerankerService()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            service.rerank("query", ["doc1", "doc2"])

        # Error message should mention load_model
        assert "load_model" in str(exc_info.value).lower()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_rerank_text_only(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService.rerank() works with text-only inputs."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Rerank text-only (using placeholder)
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents, top_k=3)

        # Should return structured results
        assert isinstance(results, list)
        assert len(results) == 3

        # Each result should have document, score, rank
        for i, result in enumerate(results):
            assert "document" in result
            assert "score" in result
            assert "rank" in result
            assert result["rank"] == i

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_rerank_multimodal(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService.rerank() works with multimodal inputs."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Create test image
        test_image = Image.new("RGB", (100, 100), color="red")

        # Rerank with multimodal query (using placeholder)
        query = {"text": "find similar content", "image": test_image}
        documents = [
            {"text": "doc1", "image": test_image},
            "doc2 text only"
        ]
        results = service.rerank(query, documents, top_k=2)

        # Should return structured results
        assert len(results) == 2

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_rerank_sorts_by_score(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService.rerank() sorts results by score descending."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Rerank (using placeholder which returns 0.8, 0.7, 0.6)
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents, top_k=3)

        # Should be sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

        # Top result should have highest score
        assert results[0]["score"] >= results[1]["score"]

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_rerank_respects_top_k(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService.rerank() respects top_k parameter."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Rerank with top_k=2 (using placeholder)
        query = "test query"
        documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        results = service.rerank(query, documents, top_k=2)

        # Should return only top_k results
        assert len(results) == 2

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_device_auto_detection(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService auto-detects device."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService(device="auto")
        service.load_model()

        # Should have detected device
        assert service.device in ["cuda", "mps", "cpu"]

        # Should pass device_map to model
        call_kwargs = mock_model_from_pretrained.call_args[1]
        assert "device_map" in call_kwargs


class TestQwen3VLRerankerServiceMultimodalFeatures:
    """Tests for multimodal-specific features."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_accepts_image_path(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService accepts image file path."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Rerank with image path (using placeholder)
        query = {"text": "query", "image": "/path/to/image.jpg"}
        documents = [{"text": "doc", "image": "/path/to/doc_image.jpg"}]
        results = service.rerank(query, documents, top_k=1)

        # Should handle image path
        assert len(results) == 1

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM.from_pretrained')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer.from_pretrained')
    def test_qwen3vl_reranker_mixed_text_and_multimodal(self, mock_tokenizer_from_pretrained, mock_model_from_pretrained):
        """Test that Qwen3VLRerankerService handles mixed text and multimodal documents."""
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Mock model and processor
        mock_model_instance = Mock()
        mock_processor_instance = Mock()
        mock_model_from_pretrained.return_value = mock_model_instance
        mock_tokenizer_from_pretrained.return_value = mock_processor_instance

        service = Qwen3VLRerankerService()
        service.load_model()

        # Rerank with mixed inputs (using placeholder)
        query = "text query"
        documents = [
            "text only doc",
            {"text": "multimodal doc", "image": Image.new("RGB", (50, 50))},
            "another text doc"
        ]
        results = service.rerank(query, documents, top_k=3)

        # Should handle mixed inputs
        assert len(results) == 3

        # All should have document field
        for result in results:
            assert "document" in result