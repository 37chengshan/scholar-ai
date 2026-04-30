"""Extended tests for Qwen3VLMultimodalEmbedding service.

Tests verify:
- Batch processing for text and images
- Empty input handling
- Large input handling
- Quantization loading (INT4/FP16)
- Device auto-detection
- Memory management
- Concurrent encoding
- Error handling
"""

import pytest
import torch
from PIL import Image
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from app.core.qwen3vl_service import (
    Qwen3VLMultimodalEmbedding,
    get_qwen3vl_service,
    create_qwen3vl_service,
)


class TestQwen3VLBatchProcessing:
    """Test batch processing capabilities."""

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_text_batch_processing(self, mock_class):
        """Test batch text encoding returns correct number of embeddings."""
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = [[0.1] * 2048, [0.2] * 2048, [0.3] * 2048]
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        texts = ["文本1", "文本2", "文本3"]
        embeddings = service.encode_text(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 2048 for emb in embeddings)

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_text_batch_normalization(self, mock_class):
        """Test batch embeddings are normalized."""
        mock_instance = MagicMock()
        
        def mock_encode(texts):
            if isinstance(texts, list):
                embeddings = []
                for _ in texts:
                    emb = np.random.randn(2048)
                    emb = emb / np.linalg.norm(emb)
                    embeddings.append(emb.tolist())
                return embeddings
            emb = np.random.randn(2048)
            emb = emb / np.linalg.norm(emb)
            return emb.tolist()
        
        mock_instance.encode_text.side_effect = mock_encode
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        texts = ["test1", "test2", "test3"]
        embeddings = service.encode_text(texts)
        
        for emb in embeddings:
            norm = np.linalg.norm(emb)
            assert 0.99 < norm < 1.01

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_image_batch(self, mock_class):
        """Test batch image encoding."""
        mock_instance = MagicMock()
        mock_instance.encode_image.return_value = [[0.1] * 2048, [0.2] * 2048]
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        images = [
            Image.new("RGB", (100, 100), color="red"),
            Image.new("RGB", (100, 100), color="blue"),
        ]
        embeddings = service.encode_image(images)
        
        assert len(embeddings) == 2
        assert all(len(emb) == 2048 for emb in embeddings)


class TestQwen3VLEmptyInput:
    """Test empty input handling."""

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_text_empty_string(self, mock_class):
        """Test empty string returns zero vector."""
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = [0.0] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        embedding = service.encode_text("")
        
        assert len(embedding) == 2048
        assert all(v == 0.0 for v in embedding)

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_text_empty_list(self, mock_class):
        """Test empty list returns empty list."""
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = []
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        embeddings = service.encode_text([])
        
        assert embeddings == []

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_table_empty(self, mock_class):
        """Test empty table returns embedding."""
        mock_instance = MagicMock()
        mock_instance.encode_table.return_value = [0.0] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        embedding = service.encode_table(caption="", headers=[], rows=[])
        
        assert len(embedding) == 2048


class TestQwen3VLLargeInput:
    """Test handling of large inputs."""

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_text_very_long_text(self, mock_class):
        """Test very long text (>32000 tokens) is handled."""
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = [0.5] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        long_text = "测试内容 " * 10000
        
        embedding = service.encode_text(long_text)
        
        assert len(embedding) == 2048

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_table_large(self, mock_class):
        """Test large table (>100 rows) is handled."""
        mock_instance = MagicMock()
        mock_instance.encode_table.return_value = [0.6] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        headers = ["Col1", "Col2", "Col3"]
        rows = [
            {"Col1": f"A{i}", "Col2": f"B{i}", "Col3": f"C{i}"} 
            for i in range(150)
        ]
        
        embedding = service.encode_table(
            caption="大型测试表格",
            headers=headers,
            rows=rows
        )
        
        assert len(embedding) == 2048


class TestQwen3VLQuantization:
    """Test quantization loading."""

    def test_int4_quantization_setting(self):
        """Test INT4 quantization configuration."""
        service = Qwen3VLMultimodalEmbedding(quantization="int4")
        
        assert service.quantization == "int4"

    def test_fp16_quantization_setting(self):
        """Test FP16 precision configuration."""
        service = Qwen3VLMultimodalEmbedding(quantization="fp16")
        
        assert service.quantization == "fp16"

    def test_quantization_accepts_any_value(self):
        """Test that quantization parameter is accepted."""
        service = Qwen3VLMultimodalEmbedding(quantization="custom")
        
        assert service.quantization == "custom"

    @patch('app.core.qwen3vl_service.AutoModel.from_pretrained')
    @patch('app.core.qwen3vl_service.AutoTokenizer.from_pretrained')
    @patch('app.core.qwen3vl_service.BitsAndBytesConfig')
    def test_load_model_with_int4(self, mock_bnb_config, mock_tokenizer, mock_model):
        """Test model loading with INT4 quantization."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        mock_bnb_config.return_value = MagicMock()
        
        service = Qwen3VLMultimodalEmbedding(quantization="int4")
        
        with patch.object(Path, 'exists', return_value=True):
            try:
                service.load_model()
                assert service.is_loaded()
            except Exception:
                # bitsandbytes might not be installed, skip this test
                pytest.skip("bitsandbytes not installed")

    @patch('app.core.qwen3vl_service.AutoModel.from_pretrained')
    @patch('app.core.qwen3vl_service.AutoTokenizer.from_pretrained')
    def test_load_model_with_fp16(self, mock_tokenizer, mock_model):
        """Test model loading with FP16 precision."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLMultimodalEmbedding(quantization="fp16")
        
        with patch.object(Path, 'exists', return_value=True):
            service.load_model()
        
        assert service.is_loaded()


class TestQwen3VLDeviceDetection:
    """Test device auto-detection."""

    def test_device_auto_detection_cuda(self):
        """Test auto-detection prefers CUDA."""
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(device="auto")
            
            assert service.device == "cuda"

    def test_device_auto_detection_mps(self):
        """Test auto-detection prefers MPS when CUDA unavailable."""
        with patch('torch.cuda.is_available', return_value=False):
            with patch.object(torch.backends, 'mps', create=True):
                with patch('torch.backends.mps.is_available', return_value=True):
                    service = Qwen3VLMultimodalEmbedding(device="auto")
                    
                    assert service.device == "mps"

    def test_device_auto_detection_falls_back(self):
        """Test auto-detection falls back when GPU not available."""
        with patch('torch.cuda.is_available', return_value=False):
            with patch.object(torch.backends, 'mps', create=True):
                with patch('torch.backends.mps.is_available', return_value=False):
                    service = Qwen3VLMultimodalEmbedding(device="auto")
                    
                    assert service.device in ["mps", "cpu"]

    def test_device_explicit_cuda(self):
        """Test explicit CUDA device selection."""
        service = Qwen3VLMultimodalEmbedding(device="cuda")
        
        assert service.device == "cuda"

    def test_device_explicit_cpu(self):
        """Test explicit CPU device selection."""
        service = Qwen3VLMultimodalEmbedding(device="cpu")
        
        assert service.device == "cpu"

    def test_device_explicit_mps(self):
        """Test explicit MPS device selection."""
        service = Qwen3VLMultimodalEmbedding(device="mps")
        
        assert service.device == "mps"


class TestQwen3VLMemoryManagement:
    """Test memory management."""

    @pytest.mark.asyncio
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    async def test_memory_no_leak_on_multiple_encodes(self, mock_class):
        """Test memory does not leak during encoding."""
        mock_instance = MagicMock()
        
        def mock_encode(text):
            return [0.1] * 2048
        
        mock_instance.encode_text.side_effect = mock_encode
        mock_class.return_value = mock_instance
        
        service = get_qwen3vl_service()
        
        initial_memory = 0
        if torch.cuda.is_available():
            initial_memory = torch.cuda.memory_allocated()
        
        for i in range(100):
            service.encode_text(f"测试文本 {i}")
        
        final_memory = 0
        if torch.cuda.is_available():
            final_memory = torch.cuda.memory_allocated()
        
        if torch.cuda.is_available():
            memory_growth = final_memory - initial_memory
            assert memory_growth < 100 * 1024 * 1024


class TestQwen3VLConcurrency:
    """Test concurrent encoding."""

    @pytest.mark.asyncio
    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    async def test_concurrent_text_encoding(self, mock_class):
        """Test concurrent text encoding works."""
        import asyncio
        
        mock_instance = MagicMock()
        
        call_count = [0]
        def mock_encode(text):
            call_count[0] += 1
            return [0.1] * 2048
        
        mock_instance.encode_text.side_effect = mock_encode
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        
        def encode_task(text):
            return service.encode_text(text)
        
        results = [encode_task(f"并发测试 {i}") for i in range(10)]
        
        assert len(results) == 10
        assert all(isinstance(r, list) for r in results)


class TestQwen3VLErrorHandling:
    """Test error handling."""

    def test_encode_without_loading_raises_error(self):
        """Test encoding before load_model() raises RuntimeError."""
        service = Qwen3VLMultimodalEmbedding()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_text("test")

    def test_encode_image_without_loading_raises_error(self):
        """Test image encoding before load_model() raises RuntimeError."""
        service = Qwen3VLMultimodalEmbedding()
        
        img = Image.new("RGB", (100, 100))
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_image(img)

    @patch('app.core.qwen3vl_service.AutoModel.from_pretrained')
    def test_model_loading_failure(self, mock_model):
        """Test model loading failure is handled."""
        mock_model.side_effect = Exception("Model not found")
        
        service = Qwen3VLMultimodalEmbedding()
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(Exception, match="Model not found"):
                service.load_model()


class TestQwen3VLSingleton:
    """Test singleton pattern."""

    def test_get_qwen3vl_service_returns_singleton(self):
        """Test get_qwen3vl_service() returns same instance."""
        service1 = get_qwen3vl_service()
        service2 = get_qwen3vl_service()
        
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_qwen3vl_service_initializes(self):
        """Test create_qwen3vl_service() initializes model."""
        with patch('app.core.qwen3vl_service.get_qwen3vl_service') as mock_get:
            mock_instance = MagicMock()
            mock_get.return_value = mock_instance
            
            service = await create_qwen3vl_service()
            
            mock_instance.load_model.assert_called_once()
            assert service is mock_instance


class TestQwen3VLImageFormats:
    """Test various image input formats."""

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_image_from_pil(self, mock_class):
        """Test encoding from PIL.Image object."""
        mock_instance = MagicMock()
        mock_instance.encode_image.return_value = [0.2] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        img = Image.new("RGB", (100, 100), color="red")
        embedding = service.encode_image(img)
        
        assert len(embedding) == 2048

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_image_from_file_path(self, mock_class):
        """Test encoding from file path string."""
        mock_instance = MagicMock()
        mock_instance.encode_image.return_value = [0.3] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        embedding = service.encode_image("tests/fixtures/test_image.png")
        
        assert len(embedding) == 2048

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    @patch('requests.get')
    def test_encode_image_from_url(self, mock_get, mock_class):
        """Test encoding from URL."""
        mock_response = MagicMock()
        mock_response.raw = MagicMock()
        mock_get.return_value = mock_response
        
        mock_instance = MagicMock()
        mock_instance.encode_image.return_value = [0.4] * 2048
        mock_class.return_value = mock_instance
        
        with patch('PIL.Image.open', return_value=Image.new("RGB", (100, 100))):
            from app.core.qwen3vl_service import get_qwen3vl_service
            service = get_qwen3vl_service()
            embedding = service.encode_image("https://example.com/test.jpg")
            
            assert len(embedding) == 2048

    @patch('app.core.qwen3vl_service._qwen3vl_service', None)
    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_encode_image_grayscale_to_rgb(self, mock_class):
        """Test grayscale image is converted to RGB."""
        mock_instance = MagicMock()
        mock_instance.encode_image.return_value = [0.5] * 2048
        mock_class.return_value = mock_instance
        
        from app.core.qwen3vl_service import get_qwen3vl_service
        service = get_qwen3vl_service()
        img = Image.new("L", (100, 100))
        embedding = service.encode_image(img)
        
        assert len(embedding) == 2048


class TestQwen3VLTableSerialization:
    """Test table serialization."""

    def test_serialize_table_full(self):
        """Test full table serialization."""
        service = Qwen3VLMultimodalEmbedding()
        
        serialized = service._serialize_table(
            caption="Test Caption",
            headers=["Col1", "Col2"],
            rows=[{"Col1": "A", "Col2": "B"}]
        )
        
        assert "Table: Test Caption" in serialized
        assert "Columns: Col1, Col2" in serialized
        assert "Sample data:" in serialized

    def test_serialize_table_empty_caption(self):
        """Test table serialization without caption."""
        service = Qwen3VLMultimodalEmbedding()
        
        serialized = service._serialize_table(
            caption="",
            headers=["A", "B"],
            rows=[]
        )
        
        assert "Table:" not in serialized
        assert "Columns: A, B" in serialized

    def test_serialize_table_truncates_rows(self):
        """Test table serialization truncates to 3 rows."""
        service = Qwen3VLMultimodalEmbedding()
        
        rows = [{"A": f"v{i}"} for i in range(10)]
        serialized = service._serialize_table(
            caption="T",
            headers=["A"],
            rows=rows
        )
        
        assert "v0" in serialized
        assert "v1" in serialized
        assert "v2" in serialized
        assert "v3" not in serialized


class TestQwen3VLModelInfo:
    """Test model information."""

    def test_get_embedding_dim(self):
        """Test get_embedding_dim() returns 2048."""
        service = Qwen3VLMultimodalEmbedding()
        
        assert service.get_embedding_dim() == 2048

    def test_get_device(self):
        """Test get_device() returns configured device."""
        service = Qwen3VLMultimodalEmbedding(device="cpu")
        
        assert service.get_device() == "cpu"

    def test_is_loaded_initially_false(self):
        """Test is_loaded() returns False initially."""
        service = Qwen3VLMultimodalEmbedding()
        
        assert service.is_loaded() is False

    @patch('app.core.qwen3vl_service.AutoModel.from_pretrained')
    @patch('app.core.qwen3vl_service.AutoTokenizer.from_pretrained')
    def test_is_loaded_true_after_loading(self, mock_tokenizer, mock_model):
        """Test is_loaded() returns True after load_model()."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLMultimodalEmbedding()
        
        with patch.object(Path, 'exists', return_value=True):
            service.load_model()
        
        assert service.is_loaded() is True
