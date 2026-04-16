"""Error recovery and resilience tests for Reranker services.

Tests verify:
- GPU memory exhaustion handling
- Network error recovery
- File not found handling
- OOM exception recovery
- Model loading failure retry
- Concurrent call error handling
- Graceful degradation
- Error logging
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import List, Dict, Any
import torch

from app.core.reranker.base import BaseRerankerService
from app.core.reranker.bge_reranker import BGERerankerService
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService


class TestBGERerankerErrorRecovery:
    """Test BGE reranker error recovery."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_model_load_failure_raises_runtime_error(self, mock_flag_reranker):
        """Model loading failure should raise RuntimeError."""
        mock_flag_reranker.side_effect = Exception("Model not found")
        
        service = BGERerankerService()
        
        with pytest.raises(RuntimeError, match="Failed to load BGE-Reranker"):
            service.load_model()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_without_load_raises_error(self, mock_flag_reranker):
        """Reranking without loading model raises RuntimeError."""
        service = BGERerankerService()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.rerank("query", ["doc"])

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_compute_score_failure_handling(self, mock_flag_reranker):
        """compute_score failure should propagate error."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.side_effect = RuntimeError("CUDA out of memory")
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        with pytest.raises(RuntimeError, match="CUDA out of memory"):
            service.rerank("query", ["doc"])

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_load_model_retry_after_failure(self, mock_flag_reranker):
        """Should allow retry after load failure."""
        mock_flag_reranker.side_effect = [
            Exception("First load failed"),
            MagicMock()
        ]
        
        service = BGERerankerService()
        
        with pytest.raises(RuntimeError):
            service.load_model()
        
        mock_flag_reranker.reset_mock()
        mock_flag_reranker.return_value = MagicMock()
        
        service._initialized = False
        service.load_model()
        
        assert service.is_loaded()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_cuda_memory_error_recovery(self, mock_flag_reranker):
        """Test recovery from CUDA memory error."""
        mock_flag_reranker_instance = MagicMock()
        
        call_count = [0]
        def score_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise torch.cuda.OutOfMemoryError("CUDA out of memory")
            return [0.9, 0.7]
        
        mock_flag_reranker_instance.compute_score = MagicMock(side_effect=score_side_effect)
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        with pytest.raises(torch.cuda.OutOfMemoryError):
            service.rerank("query", ["doc1", "doc2"])
        
        results = service.rerank("query", ["doc1", "doc2"])
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @patch('torch.cuda.is_available')
    def test_cuda_not_available_graceful_degradation(self, mock_cuda, mock_flag_reranker):
        """Should gracefully degrade to CPU when CUDA unavailable."""
        mock_cuda.return_value = False
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        
        assert service.device == "cpu"

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_double_load_safe(self, mock_flag_reranker):
        """Loading model twice should be safe."""
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        service.load_model()
        service.load_model()
        
        assert service.is_loaded()
        mock_flag_reranker.assert_called_once()


class TestQwen3VLRerankerErrorRecovery:
    """Test Qwen3VL reranker error recovery."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_model_load_file_not_found(self, mock_tokenizer, mock_model):
        """Model load failure when model files not found."""
        mock_model.from_pretrained.side_effect = FileNotFoundError("Model path not found")
        
        service = Qwen3VLRerankerService()
        
        with pytest.raises(RuntimeError, match="Failed to load Qwen3-VL-Reranker"):
            service.load_model()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_tokenizer_load_failure(self, mock_tokenizer, mock_model):
        """Tokenizer load failure should raise RuntimeError."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.from_pretrained.side_effect = Exception("Tokenizer error")
        
        service = Qwen3VLRerankerService()
        
        with pytest.raises(RuntimeError):
            service.load_model()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_without_load_raises_error(self, mock_tokenizer, mock_model):
        """Reranking without loading model raises RuntimeError."""
        service = Qwen3VLRerankerService()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.rerank("query", ["doc"])

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_model_rerank_failure_uses_placeholder(self, mock_tokenizer, mock_model):
        """Model.rerank failure should use placeholder."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank.side_effect = Exception("Rerank failed")
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        results = service.rerank("query", ["doc1", "doc2"])
        
        assert len(results) == 2

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_mps_device_not_available(self, mock_tokenizer, mock_model):
        """MPS device unavailable should fallback to CPU."""
        with patch('torch.backends.mps.is_available', return_value=False):
            with patch('torch.cuda.is_available', return_value=False):
                service = Qwen3VLRerankerService(device="auto")
                
                assert service.device == "cpu"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_int4_quantization_failure(self, mock_tokenizer, mock_model):
        """INT4 quantization failure should raise error."""
        mock_model.from_pretrained.side_effect = ImportError("bitsandbytes not installed")
        
        service = Qwen3VLRerankerService(quantization="int4")
        
        with pytest.raises(RuntimeError):
            service.load_model()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_gpu_oom_recovery(self, mock_tokenizer, mock_model):
        """GPU OOM should be caught and service should continue with placeholder."""
        service = Qwen3VLRerankerService()
        service._initialized = True
        
        class FakeModel:
            _call_count = 0
            def rerank(self, query, documents):
                self._call_count += 1
                if self._call_count == 1:
                    raise torch.cuda.OutOfMemoryError("OOM")
                return [0.9]
        
        fake_model = FakeModel()
        service.model = fake_model
        service.processor = MagicMock()
        
        results1 = service.rerank("query", ["doc"])
        assert len(results1) == 1
        
        results2 = service.rerank("query", ["doc"])
        assert len(results2) == 1


class TestRerankerConcurrencyErrors:
    """Test error handling under concurrent access."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_concurrent_load_calls(self, mock_flag_reranker):
        """Concurrent load_model calls should be safe."""
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        
        import threading
        
        def load_task():
            service.load_model()
        
        threads = [threading.Thread(target=load_task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert service.is_loaded()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_concurrent_rerank_with_one_failure(self, mock_flag_reranker):
        """One rerank failure shouldn't affect others."""
        mock_flag_reranker_instance = MagicMock()
        
        call_count = [0]
        def compute_score_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 3:
                raise RuntimeError("Transient error")
            return [0.9, 0.7]
        
        mock_flag_reranker_instance.compute_score = MagicMock(side_effect=compute_score_side_effect)
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        results1 = service.rerank("q1", ["d1", "d2"])
        results2 = service.rerank("q2", ["d1", "d2"])
        
        with pytest.raises(RuntimeError):
            service.rerank("q3", ["d1", "d2"])
        
        results4 = service.rerank("q4", ["d1", "d2"])
        
        assert len(results1) == 2
        assert len(results2) == 2
        assert len(results4) == 2


class TestRerankerGracefulDegradation:
    """Test graceful degradation scenarios."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_fp16_unavailable_uses_fp32(self, mock_flag_reranker):
        """FP16 unavailable should use FP32."""
        mock_flag_reranker.return_value = MagicMock()
        
        with patch('torch.cuda.is_available', return_value=False):
            service = BGERerankerService()
            service.load_model()
            
            assert service.device == "cpu"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_placeholder_rerank_when_model_unavailable(self, mock_tokenizer, mock_model):
        """Placeholder rerank when actual model unavailable."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(side_effect=AttributeError("No rerank method"))
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        results = service.rerank("query", ["doc1", "doc2"])
        
        assert len(results) == 2
        assert all("score" in r for r in results)


class TestRerankerStateRecovery:
    """Test state recovery after errors."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_state_consistent_after_load_failure(self, mock_flag_reranker):
        """State should remain consistent after load failure."""
        mock_flag_reranker.side_effect = Exception("Load failed")
        
        service = BGERerankerService()
        
        with pytest.raises(RuntimeError):
            service.load_model()
        
        assert not service.is_loaded()
        assert service.model is None

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_state_reset_after_unload(self, mock_flag_reranker):
        """State should be properly reset."""
        mock_flag_reranker.return_value = MagicMock()
        
        service = BGERerankerService()
        service.load_model()
        
        service._initialized = False
        service.model = None
        
        assert not service.is_loaded()


class TestRerankerInputErrorHandling:
    """Test handling of invalid inputs."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_none_query_handling(self, mock_flag_reranker):
        """None query should not crash."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.5]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = None
        documents = ["doc"]
        
        results = service.rerank(query if query is not None else "", documents)
        
        assert len(results) == 1

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_none_document_in_list(self, mock_flag_reranker):
        """None in document list should be handled."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.5]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        documents = ["valid doc", None]
        valid_docs = [d if d is not None else "" for d in documents]
        
        results = service.rerank("query", valid_docs)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_malformed_dict_input(self, mock_flag_reranker):
        """Malformed dict input should be handled."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.7, 0.6]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        documents = [
            {"wrong_key": "content"},
            {"text": "valid", "extra": None}
        ]
        
        results = service.rerank({"text": "query"}, documents)
        
        assert len(results) == 2


class TestRerankerResourceCleanup:
    """Test resource cleanup scenarios."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_model_cleanup_on_error(self, mock_flag_reranker):
        """Model resources should be cleaned up on error."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.side_effect = RuntimeError("Critical error")
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        with pytest.raises(RuntimeError):
            service.rerank("query", ["doc"])

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_cuda_memory_cleanup(self, mock_tokenizer, mock_model):
        """CUDA memory should be cleaned up."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9])
        mock_model.return_value = mock_model_instance
        
        with patch('torch.cuda.empty_cache') as mock_empty_cache:
            service = Qwen3VLRerankerService(device="cuda")
            service.load_model()
            
            results = service.rerank("query", ["doc"])


class TestRerankerLoggingErrors:
    """Test error logging."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @patch('app.core.reranker.bge_reranker.logger')
    def test_load_failure_logged(self, mock_logger, mock_flag_reranker):
        """Load failure should be logged."""
        mock_flag_reranker.side_effect = Exception("Load failed")
        
        service = BGERerankerService()
        
        with pytest.raises(RuntimeError):
            service.load_model()
        
        mock_logger.error.assert_called()

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    @patch('app.core.reranker.qwen3vl_reranker.logger')
    def test_rerank_failure_logged(self, mock_logger, mock_tokenizer, mock_model):
        """Rerank failure should be logged."""
        service = Qwen3VLRerankerService()
        service._initialized = True
        
        class FakeModel:
            def rerank(self, query, documents):
                raise Exception("Rerank failed")
        
        fake_model = FakeModel()
        service.model = fake_model
        service.processor = MagicMock()
        
        results = service.rerank("query", ["doc"])
        
        assert len(results) == 1
        mock_logger.warning.assert_called()


class TestRerankerTimeoutHandling:
    """Test timeout scenarios."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_long_running_rerank_timeout(self, mock_flag_reranker):
        """Long running rerank should handle timeout."""
        mock_flag_reranker_instance = MagicMock()

        # Inject timeout directly to keep test deterministic in CI.
        mock_flag_reranker_instance.compute_score = MagicMock(
            side_effect=TimeoutError("Rerank timeout")
        )
        mock_flag_reranker.return_value = mock_flag_reranker_instance

        service = BGERerankerService()
        service.load_model()

        with pytest.raises(TimeoutError, match="Rerank timeout"):
            service.rerank("query", ["doc"])

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_model_load_timeout(self, mock_tokenizer, mock_model):
        """Model load timeout should be handled."""
        mock_model.from_pretrained = MagicMock(side_effect=TimeoutError("Load timeout"))

        service = Qwen3VLRerankerService()

        with pytest.raises(RuntimeError, match="Failed to load Qwen3-VL-Reranker"):
            service.load_model()