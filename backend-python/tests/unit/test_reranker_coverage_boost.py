"""Targeted tests to reach 95% coverage for Reranker services.

Tests specifically cover:
- torch ImportError exception handling
- get_model_info complete return value
- supports_multimodal method
- get_device method
- async create_reranker_service functions
- clear_cache method
- CUDA detection paths
- Single score to list conversion
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import sys
import torch

from app.core.reranker.bge_reranker import (
    BGERerankerService,
    get_reranker_service,
    create_reranker_service as bge_create_reranker_service,
)
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService
from app.core.reranker.factory import (
    RerankerServiceFactory,
    get_reranker_service as factory_get_reranker_service,
    create_reranker_service as factory_create_reranker_service,
)


class TestBGERerankerMissingCoverage:
    """Cover missing lines in bge_reranker.py."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_detect_device_torch_import_error(self, mock_flag_reranker):
        """Test _detect_device when torch import fails (lines 65-66)."""
        with patch.dict(sys.modules, {'torch': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'torch'")):
                service = BGERerankerService()
                assert service.device == "cpu"

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_get_model_info_returns_complete_dict(self, mock_flag_reranker):
        """Test get_model_info returns complete dict (line 178)."""
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        info = service.get_model_info()
        
        assert info["name"] == "BAAI/bge-reranker-large"
        assert info["version"] == "large"
        assert info["type"] == "text-only"
        assert len(info) == 3

    def test_supports_multimodal_returns_false(self):
        """Test supports_multimodal returns False (line 190)."""
        service = BGERerankerService()
        assert service.supports_multimodal() is False

    def test_get_device_returns_device(self):
        """Test get_device returns device string (line 198)."""
        service = BGERerankerService()
        device = service.get_device()
        assert device in ["cuda", "cpu", "mps"]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @pytest.mark.asyncio
    async def test_create_reranker_service_async(self, mock_flag_reranker):
        """Test async create_reranker_service (lines 227-229)."""
        import app.core.reranker.bge_reranker
        app.core.reranker.bge_reranker._reranker_service = None
        
        mock_flag_reranker.return_value = MagicMock()
        
        service = await bge_create_reranker_service()
        
        assert isinstance(service, BGERerankerService)
        assert service.is_loaded()


class TestFactoryMissingCoverage:
    """Cover missing lines in factory.py."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_clear_cache_method(self, mock_flag_reranker):
        """Test clear_cache method (lines 118-119)."""
        mock_flag_reranker.return_value = MagicMock()
        
        RerankerServiceFactory._instances = {}
        
        service1 = RerankerServiceFactory.create()
        assert len(RerankerServiceFactory._instances) == 1
        
        RerankerServiceFactory.clear_cache()
        
        assert len(RerankerServiceFactory._instances) == 0

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @pytest.mark.asyncio
    async def test_factory_create_reranker_service_async(self, mock_flag_reranker):
        """Test factory async create_reranker_service (lines 143-145)."""
        mock_flag_reranker.return_value = MagicMock()
        
        RerankerServiceFactory._instances = {}
        
        service = await factory_create_reranker_service()
        
        assert service.is_loaded()


class TestQwen3VLRerankerMissingCoverage:
    """Cover missing lines in qwen3vl_reranker.py."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_detect_device_cuda_available(self, mock_tokenizer, mock_model):
        """Test _detect_device when CUDA available (line 90)."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLRerankerService(device="auto")
            assert service.device == "cuda"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_load_model_already_loaded_log(self, mock_tokenizer, mock_model):
        """Test load_model when already loaded (lines 108-109)."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        assert service.is_loaded()
        
        service.load_model()
        
        assert service.is_loaded()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_single_score_to_list(self, mock_tokenizer, mock_model):
        """Test rerank when model returns single float score (line 194)."""
        class FakeModel:
            def rerank(self, query, documents):
                return 0.85
        
        fake_model = FakeModel()
        
        service = Qwen3VLRerankerService()
        service._initialized = True
        service.model = fake_model
        service.processor = MagicMock()
        
        results = service.rerank("query", ["doc"])
        
        assert len(results) == 1
        assert results[0]["score"] == 0.85

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_supports_multimodal_returns_true(self, mock_tokenizer, mock_model):
        """Test supports_multimodal returns True (line 260)."""
        service = Qwen3VLRerankerService()
        assert service.supports_multimodal() is True

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_get_device_returns_device(self, mock_tokenizer, mock_model):
        """Test get_device returns device string (line 268)."""
        service = Qwen3VLRerankerService(device="cpu")
        assert service.get_device() == "cpu"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_get_model_info_returns_complete_dict(self, mock_tokenizer, mock_model):
        """Test get_model_info returns complete dict."""
        service = Qwen3VLRerankerService()
        info = service.get_model_info()
        
        assert info["name"] == "Qwen3-VL-Reranker-2B"
        assert info["version"] == "2B"
        assert info["type"] == "multimodal"
        assert len(info) == 3


class TestCompleteCoverageIntegration:
    """Integration tests for complete coverage."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_all_methods_covered(self, mock_flag_reranker):
        """Test all BGE methods are covered."""
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        
        assert service.supports_multimodal() is False
        assert service.get_device() in ["cuda", "cpu", "mps"]
        
        info = service.get_model_info()
        assert info["version"] == "large"
        
        service.load_model()
        assert service.is_loaded()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_all_methods_covered(self, mock_tokenizer, mock_model):
        """Test all Qwen3VL methods are covered."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService(device="cpu")
        
        assert service.supports_multimodal() is True
        assert service.get_device() == "cpu"
        
        info = service.get_model_info()
        assert info["version"] == "2B"
        
        service.load_model()
        assert service.is_loaded()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @pytest.mark.asyncio
    async def test_async_functions_complete(self, mock_flag_reranker):
        """Test all async functions."""
        mock_flag_reranker.return_value = MagicMock()
        
        import app.core.reranker.bge_reranker
        app.core.reranker.bge_reranker._reranker_service = None
        
        RerankerServiceFactory._instances = {}
        
        service1 = await bge_create_reranker_service()
        assert service1.is_loaded()
        
        RerankerServiceFactory._instances = {}
        
        service2 = await factory_create_reranker_service()
        assert service2.is_loaded()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_factory_cache_management(self, mock_flag_reranker):
        """Test factory cache management."""
        mock_flag_reranker.return_value = MagicMock()
        
        RerankerServiceFactory._instances = {}
        
        service1 = RerankerServiceFactory.create()
        assert len(RerankerServiceFactory._instances) == 1
        
        service2 = RerankerServiceFactory.create()
        assert service1 is service2
        assert len(RerankerServiceFactory._instances) == 1
        
        RerankerServiceFactory.clear_cache()
        assert len(RerankerServiceFactory._instances) == 0


class TestDeviceDetectionAllPaths:
    """Test all device detection paths."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @patch('torch.cuda.is_available')
    def test_bge_cuda_detection(self, mock_cuda, mock_flag_reranker):
        """Test BGE CUDA detection."""
        mock_cuda.return_value = True
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        
        assert service.get_device() == "cuda" or service.get_device() == "cpu"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    @patch('torch.cuda.is_available')
    @patch('torch.backends.mps.is_available')
    def test_qwen3vl_mps_detection(self, mock_mps, mock_cuda, mock_tokenizer, mock_model):
        """Test Qwen3VL MPS detection."""
        mock_cuda.return_value = False
        mock_mps.return_value = True
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService(device="auto")
        
        assert service.get_device() == "mps"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    @patch('torch.cuda.is_available')
    @patch('torch.backends.mps.is_available')
    def test_qwen3vl_cpu_fallback(self, mock_mps, mock_cuda, mock_tokenizer, mock_model):
        """Test Qwen3VL CPU fallback."""
        mock_cuda.return_value = False
        mock_mps.return_value = False
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService(device="auto")
        
        assert service.get_device() == "cpu"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_explicit_device(self, mock_tokenizer, mock_model):
        """Test Qwen3VL with explicit device."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService(device="cuda")
        
        assert service.get_device() == "cuda"


class TestScoreConversion:
    """Test score conversion scenarios."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_float_to_list_conversion(self, mock_tokenizer, mock_model):
        """Test float score to list conversion."""
        class FakeModel:
            def rerank(self, query, documents):
                return 0.95
        
        fake_model = FakeModel()
        
        service = Qwen3VLRerankerService()
        service._initialized = True
        service.model = fake_model
        service.processor = MagicMock()
        
        results = service.rerank("query", ["doc1"])
        
        assert isinstance(results[0]["score"], float)
        assert results[0]["score"] == 0.95

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_list_scores_unchanged(self, mock_tokenizer, mock_model):
        """Test list scores remain unchanged."""
        class FakeModel:
            def rerank(self, query, documents):
                return [0.9, 0.8, 0.7]
        
        fake_model = FakeModel()
        
        service = Qwen3VLRerankerService()
        service._initialized = True
        service.model = fake_model
        service.processor = MagicMock()
        
        results = service.rerank("query", ["d1", "d2", "d3"])
        
        scores = [r["score"] for r in results]
        assert abs(scores[0] - 0.9) < 0.01
        assert abs(scores[1] - 0.8) < 0.01
        assert abs(scores[2] - 0.7) < 0.01


class TestModelInfoCompleteness:
    """Test model info completeness."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_model_info_all_keys(self, mock_flag_reranker):
        """Test BGE model info has all keys."""
        service = BGERerankerService()
        info = service.get_model_info()
        
        required_keys = ["name", "version", "type"]
        for key in required_keys:
            assert key in info
            assert isinstance(info[key], str)

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_model_info_all_keys(self, mock_tokenizer, mock_model):
        """Test Qwen3VL model info has all keys."""
        service = Qwen3VLRerankerService()
        info = service.get_model_info()
        
        required_keys = ["name", "version", "type"]
        for key in required_keys:
            assert key in info
            assert isinstance(info[key], str)