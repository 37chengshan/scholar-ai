"""Multimodal search service orchestrating Milvus + ReRanker.

Provides:
- MultimodalSearchService: Unified search across text, image, table modalities
- Intent detection and modality-aware weighting
- Weighted RRF fusion of multimodal results
- Optional ReRanker integration for improved relevance

Search flow:
1. Detect query intent (image/table/default)
2. Encode query with BGE-M3
3. Search Milvus across modalities (text, image, table)
4. Apply weighted RRF fusion
5. Optionally rerank with BGE-Reranker-large

Requirements:
- RAG-03: Image search endpoint
- RAG-04: Table search endpoint
- RAG-05: Cross-modal fusion
"""

from typing import Any, Dict, List, Optional

from app.core.bge_m3_service import get_bge_m3_service
from app.core.milvus_service import get_milvus_service
from app.core.reranker_service import get_reranker_service
from app.core.modality_fusion import detect_intent, weighted_rrf_fusion, WEIGHT_PRESETS
from app.utils.logger import logger


class MultimodalSearchService:
    """Multimodal search service combining Milvus, fusion, and reranking.

    Orchestrates search across text, image, and table content types with
    intent-based weighting and optional reranking.

    Attributes:
        bge_service: BGE-M3 embedding service
        milvus: Milvus vector search service
        reranker: BGE-Reranker-large service
    """

    def __init__(self):
        """Initialize MultimodalSearchService."""
        self.bge_service = get_bge_m3_service()
        self.milvus = get_milvus_service()
        self.reranker = get_reranker_service()

    async def search(
        self,
        query: str,
        paper_ids: List[str],
        user_id: str,
        top_k: int = 10,
        use_reranker: bool = True,
        content_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute multimodal search with intent detection and fusion.

        Args:
            query: Search query string
            paper_ids: List of paper IDs to search within
            user_id: User ID for access control
            top_k: Number of final results to return
            use_reranker: Whether to apply reranking
            content_types: Content types to search (default: all)

        Returns:
            Dictionary with query, intent, weights, results, and metadata
        """
        # Step 1: Intent detection
        intent = detect_intent(query)
        weights = WEIGHT_PRESETS[intent]

        logger.info(
            "Multimodal search started",
            query=query[:50],
            intent=intent,
            paper_count=len(paper_ids),
        )

        # Step 2: Encode query with BGE-M3
        query_embedding = self.bge_service.encode_text(query)

        # Step 3: Search Milvus across modalities
        content_types = content_types or ["text", "image", "table"]
        multimodal_results: Dict[str, List[Dict[str, Any]]] = {}

        for content_type in content_types:
            try:
                # Fetch more results for RRF fusion (D-05: top_k=20)
                results = self.milvus.search_contents(
                    embedding=query_embedding,
                    user_id=user_id,
                    content_type=content_type,
                    top_k=20,
                )

                # Filter by paper_ids
                filtered = [r for r in results if r.get("paper_id") in paper_ids]
                multimodal_results[content_type] = filtered

                logger.debug(
                    f"Milvus {content_type} search",
                    results=len(results),
                    filtered=len(filtered),
                )
            except Exception as e:
                logger.error(
                    f"Milvus search failed for {content_type}",
                    error=str(e),
                )
                multimodal_results[content_type] = []

        # Step 4: Weighted RRF fusion
        fused = weighted_rrf_fusion(multimodal_results, weights)

        logger.info(
            "RRF fusion completed",
            total_results=len(fused),
            intent=intent,
        )

        # Step 5: ReRanker (optional)
        if use_reranker and len(fused) > 10:
            try:
                # Extract content for reranking
                documents = [r.get("content_data", "") for r in fused[:20]]
                reranked = self.reranker.rerank(query, documents, top_k=top_k)

                # Reorder fused results by reranked scores
                fused = self._apply_reranking(fused, reranked)

                logger.info(
                    "Reranking completed",
                    results=len(fused),
                )
            except Exception as e:
                logger.warning(
                    "Reranking failed, using RRF results",
                    error=str(e),
                )

        return {
            "query": query,
            "intent": intent,
            "weights": weights,
            "results": fused[:top_k],
            "total_count": len(fused),
        }

    def _apply_reranking(
        self,
        fused: List[Dict[str, Any]],
        reranked: List[tuple],
    ) -> List[Dict[str, Any]]:
        """Reorder fused results by reranker scores.

        Args:
            fused: List of fused results with RRF scores
            reranked: List of (document, score) tuples from reranker

        Returns:
            Reordered fused results with reranker scores
        """
        # Create document -> score mapping
        content_to_score = {doc: score for doc, score in reranked}

        # Apply reranker scores to fused results
        for result in fused:
            content = result.get("content_data", "")
            result["reranker_score"] = content_to_score.get(content, 0.0)

        # Sort by reranker score
        fused.sort(key=lambda x: x.get("reranker_score", 0.0), reverse=True)

        return fused


# Singleton instance
_multimodal_search_service: Optional[MultimodalSearchService] = None


def get_multimodal_search_service() -> MultimodalSearchService:
    """Get or create MultimodalSearchService singleton."""
    global _multimodal_search_service
    if _multimodal_search_service is None:
        _multimodal_search_service = MultimodalSearchService()
    return _multimodal_search_service