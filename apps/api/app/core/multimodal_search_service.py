"""Multimodal search service orchestrating Milvus + configured providers.

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
5. Encode expanded query with the configured embedding provider
6. Search Milvus across modalities (text, image, table)
7. Apply weighted RRF fusion
8. Optionally rerank with the configured reranker provider

Requirements:
- RAG-03: Image search endpoint
- RAG-04: Table search endpoint
- RAG-05: Cross-modal fusion
- RAG-06: Query understanding integration (per D-15)
"""

from typing import Any, Dict, List, Optional

from app.core.embedding.factory import get_embedding_service
from app.core.reranker.factory import get_reranker_service
from app.core.modality_fusion import detect_intent as detect_modality_intent, weighted_rrf_fusion, WEIGHT_PRESETS
from app.core.intent_rules import detect_intent as detect_query_intent
from app.core.synonyms import expand_query
from app.core.query_metadata_extractor import extract_metadata_filters
from app.core.query_planner import build_academic_query_plan
from app.core.retrieval_scoring import RetrievalScoringService
from app.core.retrieval_trace import RetrievalTraceService
from app.core.vector_store_repository import get_vector_store_repository
from app.models.retrieval import RetrievedChunk, SearchConstraints
from app.config import settings, resolve_model_stack
from app.utils.logger import logger


class MultimodalSearchService:
    """Multimodal search service combining Milvus, fusion, and reranking.

    Orchestrates search across text, image, and table content types with
    intent-based weighting and optional reranking.

    Attributes:
        embedding_service: Configured embedding service
        vector_store: Canonical vector store repository
        reranker: Configured reranker service
    """

    def __init__(self):
        """Initialize MultimodalSearchService."""
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store_repository()
        self.reranker = get_reranker_service()
        self.scoring = RetrievalScoringService(
            vector_weight=settings.RETRIEVAL_VECTOR_WEIGHT,
            sparse_weight=settings.RETRIEVAL_SPARSE_WEIGHT,
        )
        self.trace_service = RetrievalTraceService(
            enabled=settings.RETRIEVAL_TRACE_ENABLED
            or settings.RETRIEVAL_TRACE_INCLUDE_RESULTS
        )

    @staticmethod
    def _ensure_service_loaded(service: Any) -> None:
        """Lazily load model-backed services when startup mode is lazy."""
        is_loaded = getattr(service, "is_loaded", None)
        if callable(is_loaded) and is_loaded():
            return

        load_model = getattr(service, "load_model", None)
        if callable(load_model):
            load_model()

    @staticmethod
    def _ensure_service_loaded(service: Any) -> None:
        """Lazily load model-backed services when startup mode is lazy."""
        is_loaded = getattr(service, "is_loaded", None)
        if callable(is_loaded) and is_loaded():
            return

        load_model = getattr(service, "load_model", None)
        if callable(load_model):
            load_model()

    @staticmethod
    def _raw_score(hit: Dict[str, Any]) -> float:
        """Read vector score from canonical field with compatibility fallback."""
        score = hit.get("score")
        if score is None:
            score = hit.get("similarity")
        if score is None:
            score = 1 - float(hit.get("distance", 0.5))
        try:
            return max(0.0, min(float(score), 1.0))
        except (TypeError, ValueError):
            return 0.0

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
            text=hit.get("text") or hit.get("content_data") or hit.get("content") or "",
            text_span=hit.get("text_span"),
            score=self._raw_score(hit),
            backend=hit.get("backend", settings.VECTOR_STORE_BACKEND),
            source_id=(str(hit.get("source_id")) if hit.get("source_id") is not None else str(hit.get("id")) if hit.get("id") is not None else None),
            page_num=hit.get("page_num") or hit.get("page"),
            section_path=hit.get("section_path"),
            content_subtype=hit.get("content_subtype"),
            anchor_text=hit.get("anchor_text"),
            section=hit.get("section"),
            paper_role=hit.get("paper_role"),
            table_ref=hit.get("table_ref"),
            figure_ref=hit.get("figure_ref"),
            metric_sentence=hit.get("metric_sentence"),
            dataset=hit.get("dataset"),
            baseline=hit.get("baseline"),
            method=hit.get("method"),
            score_value=hit.get("score_value"),
            metric_name=hit.get("metric_name"),
            metric_direction=hit.get("metric_direction"),
            caption_text=hit.get("caption_text"),
            evidence_bundle_id=hit.get("evidence_bundle_id"),
            evidence_types=hit.get("evidence_types") if isinstance(hit.get("evidence_types"), list) else [],
            content_type=hit.get("content_type", "text"),
            quality_score=hit.get("quality_score"),
            raw_data=hit.get("raw_data"),
            vector_score=hit.get("vector_score"),
            sparse_score=hit.get("sparse_score"),
            hybrid_score=hit.get("hybrid_score"),
            reranker_score=hit.get("reranker_score"),
            retrieval_trace_id=hit.get("retrieval_trace_id"),
        )

    @staticmethod
    def _extract_hit_text(hit: Dict[str, Any]) -> str:
        """Extract text content from a raw hit with canonical-first order."""
        return hit.get("text") or hit.get("content_data") or hit.get("content") or ""

    def _dedupe_hits(self, hits: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
        """Deduplicate planned-query hits by semantic identity."""
        deduped: Dict[tuple, Dict[str, Any]] = {}
        for hit in hits:
            key = (
                hit.get("paper_id"),
                hit.get("content_type"),
                hit.get("page_num") or hit.get("page"),
                (self._extract_hit_text(hit)[:300] if self._extract_hit_text(hit) else ""),
            )

            existing = deduped.get(key)
            if existing is None or self._raw_score(hit) > self._raw_score(existing):
                deduped[key] = hit

        ranked = sorted(deduped.values(), key=self._raw_score, reverse=True)
        return ranked[:limit]

    @staticmethod
    def _bundle_key(hit: Dict[str, Any]) -> str:
        """Build stable bundle key for bundle-aware dedupe."""
        return (
            hit.get("evidence_bundle_id")
            or f"{hit.get('paper_id', 'unknown')}:{hit.get('table_ref') or hit.get('figure_ref') or hit.get('source_id') or hit.get('id') or 'chunk'}"
        )

    def _bundle_dedupe_hits(self, hits: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
        """Deduplicate with evidence bundle preference for academic evidence queries."""
        deduped: Dict[str, Dict[str, Any]] = {}
        for hit in hits:
            key = self._bundle_key(hit)
            existing = deduped.get(key)
            if existing is None or self._raw_score(hit) > self._raw_score(existing):
                deduped[key] = hit
        ranked = sorted(deduped.values(), key=self._raw_score, reverse=True)
        return ranked[:limit]

    @staticmethod
    def _is_weak_first_pass(fused: List[Dict[str, Any]]) -> bool:
        """Determine whether retrieval is weak enough to trigger second pass."""
        if not fused:
            return True
        top_score = max((float(item.get("hybrid_score") or item.get("score") or 0.0) for item in fused), default=0.0)
        return top_score < 0.52 or len(fused) < 3

    def compile_to_constraints(
        self,
        metadata_filters: Dict[str, Any],
        user_id: str,
        paper_ids: List[str],
    ) -> SearchConstraints:
        """Compile metadata filters into SearchConstraints.

        Per D-07: Convert extracted filters to structured constraints
        for Milvus expr pushdown.

        Args:
            metadata_filters: Dict from query_metadata_extractor
            user_id: User UUID for isolation
            paper_ids: Target paper IDs

        Returns:
            SearchConstraints for retrieval
        """
        content_types = metadata_filters.get("content_types")
        if content_types is None:
            single_content_type = metadata_filters.get("content_type")
            if isinstance(single_content_type, str) and single_content_type:
                content_types = [single_content_type]
            else:
                content_types = []

        return SearchConstraints(
            user_id=user_id,
            paper_ids=paper_ids,
            year_from=(metadata_filters.get("year_range") or (None, None))[0]
            or metadata_filters.get("year_from"),
            year_to=(metadata_filters.get("year_range") or (None, None))[1]
            or metadata_filters.get("year_to"),
            section=metadata_filters.get("section"),
            content_types=content_types,
            min_quality_score=metadata_filters.get("min_quality_score"),
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
        graph_hint: Optional[Dict[str, Any]] = None,
        graph_candidates: Optional[List[Dict[str, Any]]] = None,
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
        graph_used = bool(graph_hint and graph_hint.get("requires_graph"))
        graph_candidate_count = len(graph_candidates or [])
        graph_paper_ids = {
            str(item.get("paper_id"))
            for item in (graph_candidates or [])
            if item.get("paper_id")
        }
        narrowed_paper_ids = paper_ids
        if graph_used and graph_paper_ids:
            narrowed_paper_ids = [paper_id for paper_id in paper_ids if str(paper_id) in graph_paper_ids]
            if not narrowed_paper_ids:
                narrowed_paper_ids = paper_ids

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

        # Step 3: Academic query planning + expansion for hybrid retrieval
        academic_plan = build_academic_query_plan(query, query_intent, paper_ids=paper_ids)
        planner_queries = academic_plan.get("planner_queries") or [query]
        expanded_queries = [expand_query(q) for q in planner_queries]
        if not expanded_queries:
            expanded_queries = [expand_query(query)]

        expanded_query = expanded_queries[0]
        logger.info(f"Expanded query: {expanded_query[:100]}")

        # Step 4: Extract metadata filters per D-07
        metadata_filters = extract_metadata_filters(query)
        if metadata_filters:
            logger.info(f"Metadata filters: {metadata_filters}")

        # Compile filters to constraints for Milvus pushdown per D-07
        constraints = self.compile_to_constraints(
            metadata_filters, user_id, narrowed_paper_ids
        )

        # Step 5: Encode planned queries for dense retrieval
        self._ensure_service_loaded(self.embedding_service)
        query_embeddings = [self.embedding_service.encode_text(q) for q in expanded_queries]

        # Step 6: Search vector store across modalities with constraints pushdown
        expected_evidence_types = academic_plan.get("expected_evidence_types") or ["text", "image", "table"]
        content_types = content_types or expected_evidence_types
        multimodal_results: Dict[str, List[Dict[str, Any]]] = {}

        for content_type in content_types:
            try:
                # Run multiple planned dense queries and merge candidates.
                planned_hits: List[Dict[str, Any]] = []
                for query_embedding in query_embeddings:
                    results = self.vector_store.search(
                        embedding=query_embedding,
                        user_id=user_id,
                        content_type=content_type,
                        top_k=20,
                        constraints=constraints,
                    )
                    for result in results:
                        hit = result.model_dump()
                        hit["backend"] = result.backend
                        hit["id"] = hit.get("source_id") or f"{hit.get('paper_id', 'unknown')}-{hit.get('page_num', 0)}-{hit.get('content_type', 'text')}"
                        planned_hits.append(hit)

                if academic_plan.get("query_family") in {"compare", "numeric", "figure", "table"}:
                    multimodal_results[content_type] = self._bundle_dedupe_hits(planned_hits, limit=20)
                else:
                    multimodal_results[content_type] = self._dedupe_hits(planned_hits, limit=20)

                logger.debug(
                    f"Vector store {content_type} search with constraints pushdown",
                    results=len(multimodal_results[content_type]),
                    paper_ids_in_constraints=len(constraints.paper_ids),
                )
            except Exception as e:
                logger.error(
                    f"Vector store search failed for {content_type}",
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

        # Step 5: Hybrid dense+sparse scoring
        self.scoring.annotate_hybrid_scores(query, fused)
        fused.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)

        # Step 5.5: Second-pass rewrite when first pass retrieval is weak
        second_pass_used = False
        second_pass_gain = 0
        if self._is_weak_first_pass(fused):
            fallback_rewrites = academic_plan.get("fallback_rewrites") or []
            if fallback_rewrites:
                second_pass_used = True
                extra_embeddings = [self.embedding_service.encode_text(expand_query(rw)) for rw in fallback_rewrites[:2]]
                before_ids = {
                    f"{item.get('paper_id')}:{item.get('source_id') or item.get('id') or item.get('page_num')}"
                    for item in fused
                }
                for content_type in content_types:
                    extra_hits: List[Dict[str, Any]] = []
                    for emb in extra_embeddings:
                        try:
                            extra_results = self.vector_store.search(
                                embedding=emb,
                                user_id=user_id,
                                content_type=content_type,
                                top_k=12,
                                constraints=constraints,
                            )
                        except Exception as e:
                            logger.warning(
                                "Second-pass vector store search failed",
                                content_type=content_type,
                                error=str(e),
                            )
                            extra_results = []
                        for result in extra_results:
                            hit = result.model_dump()
                            hit["backend"] = result.backend
                            hit["id"] = hit.get("source_id") or f"{hit.get('paper_id', 'unknown')}-{hit.get('page_num', 0)}-{hit.get('content_type', 'text')}"
                            extra_hits.append(hit)

                    merged = (multimodal_results.get(content_type) or []) + extra_hits
                    if academic_plan.get("query_family") in {"compare", "numeric", "figure", "table"}:
                        multimodal_results[content_type] = self._bundle_dedupe_hits(merged, limit=24)
                    else:
                        multimodal_results[content_type] = self._dedupe_hits(merged, limit=24)

                fused = weighted_rrf_fusion(multimodal_results, weights)
                self.scoring.annotate_hybrid_scores(query, fused)
                fused.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)
                after_ids = {
                    f"{item.get('paper_id')}:{item.get('source_id') or item.get('id') or item.get('page_num')}"
                    for item in fused
                }
                second_pass_gain = max(len(after_ids - before_ids), 0)

        # Step 5.6: Graph hint retrieval narrowing (Phase 4 lightweight)
        if graph_used and graph_paper_ids:
            preferred = [item for item in fused if str(item.get("paper_id")) in graph_paper_ids]
            others = [item for item in fused if str(item.get("paper_id")) not in graph_paper_ids]
            fused = preferred + others

        # Step 6: Structured ReRanker (optional)
        if use_reranker and len(fused) > 10:
            try:
                self._ensure_service_loaded(self.reranker)
                # Build structured payload for reranking.
                documents = [self.scoring.build_structured_reranker_document(r) for r in fused[:20]]
                reranked = self.reranker.rerank(query, documents, top_k=top_k)

                # Reorder fused results by reranked scores
                fused = self.scoring.apply_reranker_scores(fused, reranked)

                logger.info(
                    "Reranking completed",
                    results=len(fused),
                )
            except Exception as e:
                logger.warning(
                    "Reranking failed, using RRF results",
                    error=str(e),
                )

        trace_payload = self.trace_service.build_trace(
            query=query,
            planner_queries=planner_queries,
            metadata_filters={
                **metadata_filters,
                "graph_retrieval_used": graph_used,
                "graph_candidate_count": graph_candidate_count,
                "graph_narrowed_paper_ids": narrowed_paper_ids,
                "use_reranker": bool(use_reranker),
                "embedding_model": settings.EMBEDDING_MODEL,
                "reranker_model": settings.RERANKER_MODEL,
                "model_stack": resolve_model_stack(
                    settings.RETRIEVAL_MODEL_STACK,
                    settings.EMBEDDING_MODEL,
                    settings.RERANKER_MODEL,
                ),
            },
            weights=weights,
            results=fused,
        )

        # Step 7: Intent-based result formatting (per D-15)
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
            "query_family": academic_plan.get("query_family"),
            "planner_queries": planner_queries,
            "planner_query_count": len(planner_queries),
            "decontextualized_query": academic_plan.get("decontextualized_query"),
            "second_pass_used": second_pass_used,
            "second_pass_gain": second_pass_gain,
            "expected_evidence_types": expected_evidence_types,
            "retrieval_mode": "hybrid_dense_sparse",
            "metadata_filters": metadata_filters,
            "weights": weights,
            "results": final_results,
            "total_count": len(fused),
            "vector_backend": settings.VECTOR_STORE_BACKEND,
            "use_reranker": bool(use_reranker),
            "embedding_model": settings.EMBEDDING_MODEL,
            "reranker_model": settings.RERANKER_MODEL,
            "model_stack": resolve_model_stack(
                settings.RETRIEVAL_MODEL_STACK,
                settings.EMBEDDING_MODEL,
                settings.RERANKER_MODEL,
            ),
            "graph_retrieval_used": graph_used,
            "graph_candidate_count": graph_candidate_count,
            "graph_vector_merged_evidence": len(final_results),
            "graph_narrowed_paper_ids": narrowed_paper_ids,
        }

        if trace_payload is not None:
            response["trace"] = trace_payload
        
        # Add intent-specific fields
        response.update(additional_fields)
        
        return response


# Singleton instance
_multimodal_search_service: Optional[MultimodalSearchService] = None


def get_multimodal_search_service() -> MultimodalSearchService:
    """Get or create MultimodalSearchService singleton."""
    global _multimodal_search_service
    if _multimodal_search_service is None:
        _multimodal_search_service = MultimodalSearchService()
    return _multimodal_search_service