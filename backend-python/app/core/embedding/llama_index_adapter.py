"""LlamaIndex adapter for Qwen3VLEmbeddingService.

Provides compatibility layer between Qwen3VL and LlamaIndex's embedding interface.
Used for semantic chunking with SemanticSplitterNodeParser.

Example:
    from app.core.embedding.llama_index_adapter import Qwen3VLLlamaIndexEmbedding
    
    embed_model = Qwen3VLLlamaIndexEmbedding()
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model
    )
"""

from typing import Any, List, Optional
from llama_index.core.base.embeddings.base import BaseEmbedding


class Qwen3VLLlamaIndexEmbedding(BaseEmbedding):
    """LlamaIndex adapter for Qwen3VLEmbeddingService.
    
    Wraps Qwen3VLEmbeddingService to provide LlamaIndex-compatible interface.
    Uses Qwen3VL 2048-dim embeddings instead of BGE-M3 1024-dim.
    
    Features:
    - 2048-dimensional embeddings (Qwen3VL)
    - Compatible with SemanticSplitterNodeParser
    - Auto-loads model on first use
    """
    
    def __init__(
        self,
        model_name: str = "Qwen3-VL-Embedding-2B",
        quantization: str = "int4",
        device: str = "auto",
        **kwargs: Any
    ) -> None:
        """Initialize Qwen3VL adapter for LlamaIndex.
        
        Args:
            model_name: Model identifier (for compatibility, not used)
            quantization: Quantization type ("int4" or "fp16")
            device: Device to use ("auto", "cuda", "mps", or "cpu")
            **kwargs: Additional arguments for LlamaIndex compatibility
        """
        super().__init__(**kwargs)
        self._service = None
        self._quantization = quantization
        self._device = device
        self._model_name = model_name
        self._model_loaded = False
    
    def _get_service(self):
        """Lazy load Qwen3VL service with auto model loading."""
        if self._service is None:
            from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
            self._service = Qwen3VLEmbeddingService(
                quantization=self._quantization,
                device=self._device
            )
        return self._service
    
    def _ensure_model_loaded(self):
        """Ensure model is loaded, load if necessary."""
        if not self._model_loaded:
            service = self._get_service()
            if not service.is_loaded():
                service.load_model()
            self._model_loaded = True
    
    @classmethod
    def class_name(cls) -> str:
        """Return class name for LlamaIndex serialization."""
        return "Qwen3VLLlamaIndexEmbedding"
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Asynchronous query embedding (calls sync version)."""
        return self._get_query_embedding(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Asynchronous text embedding (calls sync version)."""
        return self._get_text_embedding(text)
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a query.
        
        Args:
            query: Query text to embed
            
        Returns:
            2048-dimensional embedding vector
        """
        self._ensure_model_loaded()
        service = self._get_service()
        result = service.encode_text(query)
        return result if isinstance(result, list) and len(result) > 0 and isinstance(result[0], float) else result[0]
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text.
        
        Args:
            text: Text to embed
            
        Returns:
            2048-dimensional embedding vector
        """
        self._ensure_model_loaded()
        service = self._get_service()
        result = service.encode_text(text)
        return result if isinstance(result, list) and len(result) > 0 and isinstance(result[0], float) else result[0]
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of 2048-dimensional embedding vectors
        """
        self._ensure_model_loaded()
        service = self._get_service()
        return service.encode_text(texts)
    
    @property
    def embed_dim(self) -> int:
        """Return embedding dimension."""
        return 2048
    
    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model_name


def get_qwen3vl_llama_index_embedding(
    quantization: str = "int4",
    device: str = "auto"
) -> Qwen3VLLlamaIndexEmbedding:
    """Get Qwen3VL embedding adapter for LlamaIndex.
    
    Convenience function for creating the adapter.
    
    Args:
        quantization: Quantization type ("int4" or "fp16")
        device: Device to use ("auto", "cuda", "mps", or "cpu")
    
    Returns:
        Qwen3VLLlamaIndexEmbedding instance
    """
    return Qwen3VLLlamaIndexEmbedding(
        quantization=quantization,
        device=device
    )
