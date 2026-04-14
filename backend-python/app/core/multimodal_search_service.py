"""Multimodal search service orchestrating Milvus + ReRanker.

Provides:
- MultimodalSearchService: Unified search across text, image, table modalities
- Intent detection and modality-aware weighting
- Weighted RRF fusion of multimodal results
- Optional ReRanker integration for improved relevance
- Query understanding integration (intent, expansion, metadata)

Search flow:
1. Detect query intent (question/compare/summary/evolution) via intent_rules
2. Detect modality intent (image/table/default) via modality_fusion
3. Expand query with synonyms
4. Extract metadata filters
5. Encode expanded query with BGE-M3
6. Search Milvus across modalities (text, image, table)
7. Apply weighted RRF fusion
8. Optionally rerank with BGE-Reranker-large

Requirements:
- RAG-03: Image search endpoint
- RAG-04: Table search endpoint
- RAG-05: Cross-modal fusion
- RAG-06: Query understanding integration (per D-15)
"""

from typing import Any, Dict, List, Optional

from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.milvus_service import get_milvus_service
from app.core.reranker_service import get_reranker_service
from app.core.modality_fusion import detect_intent as detect_modality_intent, weighted_rrf_fusion, WEIGHT_PRESETS
from app.core.intent_rules import detect_intent as detect_query_intent
from app.core.synonyms import expand_query
from app.core.query_metadata_extractor import extract_metadata_filters
from app.models.retrieval import RetrievedChunk
from app.utils.logger import logger


class MultimodalSearchService:
    """Multimodal search service combining Milvus, fusion, and reranking.

    Orchestrates search across text, image, and table content types with
    intent-based weighting and optional reranking.

    Attributes:
        qwen3vl_service: Qwen3VL multimodal embedding service (2048-dim)
        milvus: Milvus vector search service
        reranker: BGE-Reranker-large service
    """

    def __init__(self):
        """Initialize MultimodalSearchService."""
        self.qwen3vl_service = get_qwen3vl_service()
        self.milvus = get_milvus_service()
        self.reranker = get_reranker_service()

    def _normalize_hit(self, hit: Dict[str, Any]) -> RetrievedChunk:
        """Normalize Milvus Raw Hit to unified RetrievedChunk schema.

        Field mapping per Phase 40 D-02:
        - content_data -> text (fallback: content)
        - score -> score (fallback: similarity, distance)
        - page_num -> page_num (fallback: page)

        Args:
            hit: Raw hit dict from Milvus search_contents_v2()

        Returns:
            RetrievedChunk with unified field names
        """
        return RetrievedChunk(
            paper_id=hit.get("paper_id", ""),
            paper_title=hit.get("paper_title"),
            text=hit.get("content_data") or hit.get("content") or "",
            score=float(hit.get("score") or hit.get("similarity") or (1 - hit.get("distance", 0.5))),
            page_num=hit.get("page_num") or hit.get("page"),
            section=hit.get("section"),
            content_type=hit.get("content_type", "text"),
            quality_score=hit.get("quality_score"),
            raw_data=hit.get("raw_data"),
        )

    def _format_compare_response(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format results for compare intent - group by paper.

        Per D-15: Intent-based post-processing for compare queries.

        Args:
            results: List of search results

        Returns:
            List grouped by paper_id: [{"paper_id": pid, "results": [...]}, ...]
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        
        for result in results:
            paper_id = result.get("paper_id", "unknown")
            if paper_id not in grouped:
                grouped[paper_id] = []
            grouped[paper_id].append(result)
        
        # Convert to list format
        return [
            {"paper_id": paper_id, "results": paper_results}
            for paper_id, paper_results in grouped.items()
        ]

    def _format_summary_response(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format results for summary intent - extract key points.

        Per D-15: Intent-based post-processing for summary queries.

        Args:
            results: List of search results

        Returns:
            Dict with key_points (top 3) and total_chunks count
        """
        return {
            "key_points": results[:3] if len(results) > 3 else results,
            "total_chunks": len(results),
        }

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
            Dictionary with query, intent, expanded_query, metadata_filters, weights, results, and metadata
        """
        # Step 1: Detect query intent (question/compare/summary/evolution) per D-15
        query_intent = detect_query_intent(query)
        logger.info(f"Detected intent: {query_intent} for query: {query[:50]}")

        # Step 2: Detect modality intent (image/table/default) for weights
        modality_intent = detect_modality_intent(query)
        weights = WEIGHT_PRESETS[modality_intent]

        logger.info(
            "Multimodal search started",
            query=query[:50],
            intent=query_intent,
            modality=modality_intent,
            paper_count=len(paper_ids),
        )

        # Step 3: Expand query with synonyms per D-04
        expanded_query = expand_query(query)
        logger.info(f"Expanded query: {expanded_query[:100]}")

        # Step 4: Extract metadata filters per D-07
        metadata_filters = extract_metadata_filters(query)
        if metadata_filters:
            logger.info(f"Metadata filters: {metadata_filters}")

        # Step 5: Encode expanded query with Qwen3VL (2048-dim)
        query_embedding = self.qwen3vl_service.encode_text(expanded_query)

        # Step 3: Search Milvus across modalities
        content_types = content_types or ["text", "image", "table"]
        multimodal_results: Dict[str, List[Dict[str, Any]]] = {}

        for content_type in content_types:
            try:
                results = self.milvus.search_contents_v2(
                    embedding=query_embedding,
                    user_id=user_id,
                    content_type=content_type,
                    top_k=20,
                )

                # Filter by paper_ids (only if paper_ids is provided)
                if paper_ids:
                    filtered = [r for r in results if r.get("paper_id") in paper_ids]
                else:
                    filtered = results  # No filter if paper_ids is empty
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
            intent=query_intent,
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

        # Step 6: Intent-based result formatting (per D-15)
        # Normalize fused results to unified schema per D-02
        normalized_fused = [self._normalize_hit(r).model_dump() for r in fused]
        final_results = normalized_fused[:top_k]
        additional_fields = {}
        
        if query_intent == "compare":
            # Add grouped_by_paper for compare intent
            grouped_results = self._format_compare_response(normalized_fused[:top_k])
            additional_fields["grouped_by_paper"] = grouped_results
            logger.info("Applied compare formatting", groups=len(grouped_results))
        elif query_intent == "summary":
            # Add key_points for summary intent
            summary_format = self._format_summary_response(normalized_fused)
            additional_fields["key_points"] = summary_format["key_points"]
            additional_fields["total_chunks"] = summary_format["total_chunks"]
            logger.info("Applied summary formatting", key_points=len(summary_format["key_points"]))

        # Build response
        response = {
            "query": query,
            "expanded_query": expanded_query,
            "intent": modality_intent,
            "query_intent": query_intent,
            "metadata_filters": metadata_filters,
            "weights": weights,
            "results": final_results,
            "total_count": len(fused),
        }
        
        # Add intent-specific fields
        response.update(additional_fields)
        
        return response

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