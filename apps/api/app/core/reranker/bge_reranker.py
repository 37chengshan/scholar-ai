"""BGE-Reranker adapter implementing BaseRerankerService.

Provides:
- BGE-Reranker-large model adapter
- Text-only reranking (supports_multimodal=False)
- Structured output format (document, score, rank)
- Backward compatibility with old ReRankerService
- Singleton pattern via get_reranker_service()

Design decisions (per D-R03):
- Preserves existing ReRankerService behavior
- Returns structured results instead of tuples
- Accepts dict inputs but uses text component
- FP16 optimization for CUDA devices
"""

from typing import List, Dict, Any, Union, Optional

try:
    from FlagEmbedding import FlagReranker
    _FLAG_EMBEDDING_IMPORT_ERROR: Optional[Exception] = None
except Exception as import_error:  # pragma: no cover - depends on local ML env
    FlagReranker = None  # type: ignore[assignment]
    _FLAG_EMBEDDING_IMPORT_ERROR = import_error

from app.core.reranker.base import BaseRerankerService
from app.utils.logger import logger


class BGERerankerService(BaseRerankerService):
    """BGE-Reranker-large adapter for text-only reranking.
    
    Features:
    - Cross-encoder architecture for precise relevance scoring
    - FP16 mode for memory efficiency on CUDA
    - Normalized scores (0-1 range)
    - Structured output: {"document": ..., "score": ..., "rank": ...}
    
    Note:
        Text-only reranker (supports_multimodal=False).
        Accepts dict inputs but uses text component only.
    
    Example:
        service = BGERerankerService()
        service.load_model()
        results = service.rerank("query", ["doc1", "doc2"], top_k=5)
        # Returns: [{"document": "doc1", "score": 0.9, "rank": 0}, ...]
    """

    MODEL_NAME = "BAAI/bge-reranker-large"

    def __init__(self):
        """Initialize BGE-Reranker service.
        
        Detects device (cuda/cpu) automatically.
        Model not loaded until load_model() called.
        """
        self.model: Optional[Any] = None
        self.device = self._detect_device()
        self._initialized = False

    def _detect_device(self) -> str:
        """Detect best available device (cuda/cpu).
        
        Returns:
            "cuda" if CUDA available, "cpu" otherwise
        """
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def load_model(self) -> None:
        """Load BGE-Reranker-large model into memory.
        
        Called at app startup. Uses FP16 on CUDA for memory efficiency.
        
        Raises:
            RuntimeError: If model loading fails
        """
        if self._initialized:
            logger.info("BGE-Reranker model already loaded, skipping")
            return

        if FlagReranker is None:
            raise RuntimeError(
                "FlagEmbedding import failed. "
                f"Cannot load BGE-Reranker model: {_FLAG_EMBEDDING_IMPORT_ERROR}"
            )

        try:
            logger.info(
                "Loading BGE-Reranker model",
                model=self.MODEL_NAME,
                device=self.device,
            )

            # Use FP16 for CUDA devices
            use_fp16 = self.device == "cuda"
            self.model = FlagReranker(
                self.MODEL_NAME,
                use_fp16=use_fp16,
            )
            self._initialized = True

            logger.info(
                "BGE-Reranker model loaded successfully",
                device=self.device,
                use_fp16=use_fp16,
            )
        except Exception as e:
            logger.error("Failed to load BGE-Reranker model", error=str(e))
            raise RuntimeError(f"Failed to load BGE-Reranker model: {e}")

    def rerank(
        self,
        query: Union[str, Dict[str, Any]],
        documents: List[Union[str, Dict[str, Any]]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank documents by relevance to query.
        
        Args:
            query: Query string or dict with "text" key
                - String: "search query"
                - Dict: {"text": "query", ...}  (uses text only)
            documents: List of document strings or dicts
                - Strings: ["doc1", "doc2"]
                - Dicts: [{"text": "doc", ...}, ...]  (uses text only)
            top_k: Number of top results to return
            
        Returns:
            List of dicts sorted by score descending:
            [{"document": str/dict, "score": float, "rank": int}, ...]
            Top result has rank=0, score closest to 1.0
            
        Raises:
            RuntimeError: If model not loaded
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Extract text from dict inputs (if provided)
        query_text = query if isinstance(query, str) else query.get("text", "")
        doc_texts = [
            doc if isinstance(doc, str) else doc.get("text", "")
            for doc in documents
        ]

        # Create query-document pairs for cross-encoder
        pairs = [[query_text, doc] for doc in doc_texts]

        # Compute relevance scores with normalization
        scores = self.model.compute_score(pairs, normalize=True)

        # Handle single document case (compute_score returns float)
        if isinstance(scores, float):
            scores = [scores]

        # Sort by score descending and create structured results
        scored_docs = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

        # Return structured format
        results = [
            {
                "document": doc,
                "score": float(score),
                "rank": i
            }
            for i, (doc, score) in enumerate(scored_docs[:top_k])
        ]

        return results

    def is_loaded(self) -> bool:
        """Check if model is loaded and ready for use.
        
        Returns:
            True if model loaded, False otherwise
        """
        return self._initialized

    def get_model_info(self) -> Dict[str, str]:
        """Return model name and version information.
        
        Returns:
            Dict with model metadata
        """
        return {
            "name": self.MODEL_NAME,
            "version": "large",
            "type": "text-only",
        }

    def supports_multimodal(self) -> bool:
        """Check if reranker supports multimodal inputs.
        
        Returns:
            False (BGE-Reranker is text-only)
        """
        return False

    def get_device(self) -> str:
        """Get the device being used (cuda/cpu).
        
        Returns:
            Device string ("cuda" or "cpu")
        """
        return self.device


# Singleton instance (backward compatibility)
_reranker_service: Optional[BGERerankerService] = None


def get_reranker_service() -> BGERerankerService:
    """Get or create BGERerankerService singleton.
    
    Backward compatible function preserving old API.
    
    Returns:
        BGERerankerService instance (singleton)
    """
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = BGERerankerService()
    return _reranker_service


async def create_reranker_service() -> BGERerankerService:
    """Create and initialize BGERerankerService.
    
    Backward compatible async function.
    
    Returns:
        Initialized BGERerankerService instance
    """
    service = get_reranker_service()
    service.load_model()
    return service