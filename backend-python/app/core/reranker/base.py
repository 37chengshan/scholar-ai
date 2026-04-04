"""BaseRerankerService abstract interface for reranker services.

Provides:
- Abstract interface for all reranker implementations
- Support for text and multimodal inputs
- Model lifecycle management
- Backward compatibility with existing ReRankerService

Design decisions (per D-R01):
- Unified interface supports text-only and multimodal rerankers
- Configuration-driven model selection via factory
- Structured return format (document, score, rank)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union


class BaseRerankerService(ABC):
    """Abstract interface for reranker services.
    
    All reranker implementations must inherit from this base class
    and implement the abstract methods.
    
    Features:
    - Text and multimodal input support
    - Model lifecycle management (load, is_loaded)
    - Structured output format (document, score, rank)
    - Model information retrieval
    
    Example implementation:
        class BGERerankerService(BaseRerankerService):
            def supports_multimodal(self) -> bool:
                return False  # Text-only reranker
            
            def rerank(self, query, documents, top_k=10):
                # Implementation using BGE-Reranker-large
                ...
    """

    @abstractmethod
    def load_model(self) -> None:
        """Load model into memory.
        
        Called at application startup to initialize the reranker model.
        Should set internal state to indicate model is loaded.
        
        Raises:
            RuntimeError: If model loading fails
        """
        pass

    @abstractmethod
    def rerank(
        self,
        query: Union[str, Dict[str, Any]],
        documents: List[Union[str, Dict[str, Any]]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank documents by relevance to query.
        
        Args:
            query: Query string (text-only) or dict (multimodal with text + image)
                - Text: "search query"
                - Multimodal: {"text": "query", "image": PIL.Image or path}
            documents: List of document strings or multimodal dicts
                - Text: ["doc1", "doc2"]
                - Multimodal: [{"text": "doc", "image": ...}, ...]
            top_k: Number of top results to return
            
        Returns:
            List of dicts sorted by score descending:
            [
                {"document": str/dict, "score": float, "rank": int},
                ...
            ]
            Top result has rank=0, score closest to 1.0
            
        Raises:
            RuntimeError: If model not loaded (call load_model() first)
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready for use.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Return model name and version information.
        
        Returns:
            Dict with keys:
            - "name": Model name/identifier
            - "version": Model version or "unknown"
            - "type": "text-only" or "multimodal"
        """
        pass

    @abstractmethod
    def supports_multimodal(self) -> bool:
        """Check if reranker supports multimodal inputs.
        
        Returns:
            True if reranker can process images + text
            False if reranker only processes text
        """
        pass