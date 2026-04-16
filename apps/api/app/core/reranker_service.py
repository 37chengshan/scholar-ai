"""ReRanker service using BGE-Reranker-large model.

Provides:
- Reranking of search results by relevance
- Singleton pattern for model efficiency
- FP16 optimization for memory efficiency
- Batch reranking support

BGE-Reranker-large is used to improve retrieval quality by
reranking initial Milvus search results.
"""

from typing import List, Tuple, Optional

from FlagEmbedding import FlagReranker

from app.utils.logger import logger


class ReRankerService:
    """BGE-Reranker-large service for result reranking.

    Features:
    - Cross-encoder architecture for precise relevance scoring
    - FP16 mode for memory efficiency
    - Batch reranking support
    - Normalized scores
    """

    MODEL_NAME = "BAAI/bge-reranker-large"

    def __init__(self):
        self.model: Optional[FlagReranker] = None
        self.device = "cuda" if self._check_cuda() else "cpu"
        self._initialized = False

    def _check_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self) -> None:
        """Load model into memory. Called at app startup."""
        if self._initialized:
            return

        try:
            logger.info(
                "Loading ReRanker model",
                model=self.MODEL_NAME,
                device=self.device,
            )

            # Load with FP16 for memory efficiency
            use_fp16 = self.device == "cuda"
            self.model = FlagReranker(
                self.MODEL_NAME,
                use_fp16=use_fp16,
            )
            self._initialized = True

            logger.info(
                "ReRanker model loaded successfully",
                device=self.device,
                use_fp16=use_fp16,
            )
        except Exception as e:
            logger.error("Failed to load ReRanker model", error=str(e))
            raise

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Rerank documents by relevance to query.

        Args:
            query: Search query string
            documents: List of document texts to rerank
            top_k: Number of top results to return

        Returns:
            List of (document, score) tuples sorted by score descending
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Create query-document pairs for cross-encoder
        pairs = [[query, doc] for doc in documents]

        # Compute relevance scores with normalization
        scores = self.model.compute_score(pairs, normalize=True)

        # Handle single document case (compute_score returns float)
        if isinstance(scores, float):
            scores = [scores]

        # Sort by score descending and return top_k
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def get_device(self) -> str:
        """Get the device being used (cuda/cpu)."""
        return self.device


# Singleton instance
_reranker_service: Optional[ReRankerService] = None


def get_reranker_service() -> ReRankerService:
    """Get or create ReRankerService singleton."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = ReRankerService()
    return _reranker_service


async def create_reranker_service() -> ReRankerService:
    """Create and initialize ReRankerService.

    Returns:
        Initialized ReRankerService instance
    """
    service = get_reranker_service()
    service.load_model()
    return service