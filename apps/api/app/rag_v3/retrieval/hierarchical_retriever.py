"""HierarchicalRetriever: v3 RAPTOR-style two-level retrieval orchestrator.

Phase 1 design:
  Step 0: Extract any paper ID literals from query (e.g. "v2-p-001")
  Level 0: Paper-level TF-IDF index → identify candidate paper set
  Level 1: Section-level TF-IDF index → within candidate papers
  Level 2: Dense Milvus search → final evidence candidates
           - If paper IDs found in query, apply Milvus paper_id filter
  Level 3 (optional): RAPTOR tree-level search for multi-granularity retrieval
  Fusion: RRF across dense + section + tree signals
"""
from __future__ import annotations

import os
import time

import structlog

from app.rag_v3.evaluation.retrieval_evaluator import evaluate_evidence_pack
from app.rag_v3.fusion.candidate_balancer import balance_candidates
from app.rag_v3.fusion.rrf_fusion import rrf_fuse, trim_candidates
from app.rag_v3.indexes.paper_index import PaperSummaryIndex
from app.rag_v3.indexes.section_index import SectionSummaryIndex
from app.rag_v3.planner.query_family_router import normalize_query_family
from app.rag_v3.planner.query_plan import apply_retrieval_depth_override, build_query_plan
from app.rag_v3.rerank.qwen3vl_rerank_adapter import rerank_candidates
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever, extract_paper_ids_from_query
from app.rag_v3.schemas import EvidenceCandidate, EvidencePack

logger = structlog.get_logger()

# Feature flag for RAPTOR tree-level search
RAPTOR_ENABLED = os.getenv("RAPTOR_ENABLED", "false").lower() in {"true", "1", "yes"}
RAPTOR_SEARCH_TIMEOUT_MS = 200

_RETRIEVAL_DEPTH_RANK = {
    "shallow": 1.0,
    "medium": 2.0,
    "deep": 3.0,
}


class HierarchicalRetriever:
    """v3 retrieval orchestrator with real two-level hierarchical retrieval."""

    def __init__(
        self,
        *,
        paper_index: PaperSummaryIndex | None = None,
        section_index: SectionSummaryIndex | None = None,
        dense_retriever: DenseEvidenceRetriever | None = None,
        raptor_tree_index: Any | None = None,
        embedding_provider: Any | None = None,
    ) -> None:
        self._paper_index = paper_index or PaperSummaryIndex()
        self._section_index = section_index or SectionSummaryIndex()
        self._dense_retriever = dense_retriever or DenseEvidenceRetriever()
        self._raptor_tree_index = raptor_tree_index
        self._embedding_provider = embedding_provider
        self._query_counter = 0

    def retrieve_evidence(
        self,
        query: str,
        query_family: str,
        stage: str,
        top_k: int = 10,
        paper_scope: list[str] | None = None,
        retrieval_depth: str | None = None,
        section_paths: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        content_types: list[str] | None = None,
        user_id: str = "",
    ) -> EvidencePack:
        plan = build_query_plan(query=query, query_family=query_family)
        plan = apply_retrieval_depth_override(plan, retrieval_depth)
        family = normalize_query_family(plan.query_family)

        # Step 0: Extract explicit scope and any paper ID literals from query.
        scoped_paper_ids = [paper_id for paper_id in dict.fromkeys(paper_scope or []) if paper_id]
        query_paper_ids = extract_paper_ids_from_query(query)

        # Level 0: Paper-level TF-IDF retrieval → identify candidate paper set
        top_paper_artifacts = self._paper_index.search(query=query, top_k=plan.paper_top_k)
        paper_candidate_ids = {art.paper_id for art in top_paper_artifacts}

        # Combine: query-extracted IDs take priority (they are explicit references)
        effective_paper_ids: list[str] | None = None
        if scoped_paper_ids:
            effective_paper_ids = scoped_paper_ids
            all_filter_ids = scoped_paper_ids[:10]
        elif query_paper_ids:
            effective_paper_ids = query_paper_ids
            # Also include TF-IDF neighbors (cross-paper queries may reference multiple)
            all_filter_ids = list(dict.fromkeys(query_paper_ids + list(paper_candidate_ids)))[:10]
        else:
            all_filter_ids = list(paper_candidate_ids)[:10]

        # Level 2: Dense Milvus search with optional paper filter
        dense_top_k = min(plan.dense_chunk_top_k, 100)
        if effective_paper_ids:
            # Primary: filter by query-referenced papers
            dense_candidates = self._dense_retriever.retrieve(
                query=query,
                top_k=dense_top_k,
                paper_id_filter=effective_paper_ids,
                section_paths=section_paths,
                page_from=page_from,
                page_to=page_to,
                content_types=content_types,
            )
            # Query-literal references can broaden to global recall if the filtered
            # branch comes back thin. Explicit API paper scope must stay scoped.
            if len(dense_candidates) < top_k and not scoped_paper_ids:
                extra = self._dense_retriever.retrieve(
                    query=query,
                    top_k=min(plan.dense_chunk_top_k, max(top_k * 2, top_k)),
                    section_paths=section_paths,
                    page_from=page_from,
                    page_to=page_to,
                    content_types=content_types,
                )
                seen = {c.source_chunk_id for c in dense_candidates}
                for c in extra:
                    if c.source_chunk_id not in seen:
                        dense_candidates.append(c)
                        seen.add(c.source_chunk_id)
        else:
            dense_candidates = self._dense_retriever.retrieve(
                query=query,
                top_k=dense_top_k,
                section_paths=section_paths,
                page_from=page_from,
                page_to=page_to,
                content_types=content_types,
            )

        # Level 1: Section-level candidates from identified papers
        section_candidates = self._retrieve_section_candidates(
            query=query,
            paper_ids=set(effective_paper_ids or []) | paper_candidate_ids,
            dense_candidates=dense_candidates,
            section_top_k_per_paper=plan.section_top_k_per_paper,
        )

        # Merge source candidates for RRF fusion
        source_candidates: dict[str, list[EvidenceCandidate]] = {
            "dense": dense_candidates,
            "section": section_candidates,
        }

        # Level 3 (optional): RAPTOR tree-level search
        tree_candidates = self._retrieve_tree_candidates(
            query=query,
            paper_ids=effective_paper_ids,
            user_id=user_id,
        )
        if tree_candidates:
            source_candidates["tree"] = tree_candidates

        fused = rrf_fuse(source_candidates)
        balanced = balance_candidates(
            candidates=fused,
            query_family=family,
            per_paper_min_quota=2,
            max_candidates=plan.candidate_pool_max,
        )

        reranked = rerank_candidates(query=query, candidates=balanced)
        final_candidates = trim_candidates(reranked, min(top_k, plan.rerank_top_k))

        # Guarantee: if query named specific papers but none appear in top results,
        # force-insert at least 1 section candidate from each named paper.
        if effective_paper_ids:
            retrieved_pids = {c.paper_id for c in final_candidates}
            forced: list[EvidenceCandidate] = []
            for forced_pid in effective_paper_ids:
                if forced_pid not in retrieved_pids:
                    forced_secs = self._section_index.search_for_paper(forced_pid, query=query, top_k=2)
                    for sec in forced_secs:
                        for chunk_id in sec.source_chunk_ids[:1]:
                            forced.append(
                                EvidenceCandidate(
                                    source_chunk_id=chunk_id,
                                    paper_id=sec.paper_id,
                                    section_id=sec.section_id,
                                    content_type="text",
                                    anchor_text=sec.section_summary[:200],
                                    candidate_sources=["forced_section"],
                                    rrf_score=0.5,
                                )
                            )
                            break
            # Prepend forced candidates so they appear in top-k
            if forced:
                final_candidates = forced + final_candidates[: max(0, top_k - len(forced))]

        self._query_counter += 1
        query_id = f"v3-q-{self._query_counter:06d}"

        pack = EvidencePack(
            query_id=query_id,
            query=query,
            query_family=family,
            stage=stage,
            candidates=final_candidates,
            diagnostics={
                "candidate_pool_size": float(len(balanced)),
                "dense_retrieved": float(len(dense_candidates)),
                "section_candidates": float(len(section_candidates)),
                "paper_index_size": float(len(self._paper_index)),
                "section_index_size": float(len(self._section_index)),
                "query_paper_ids_count": float(len(query_paper_ids)),
                "explicit_paper_scope_count": float(len(scoped_paper_ids)),
                "paper_filter_applied": float(1 if effective_paper_ids else 0),
                "dense_fallback_used": float(1 if self._dense_retriever.last_trace.get("fallback_used") else 0),
                "dense_unsupported_field_type_count": float(self._dense_retriever.unsupported_field_type_count),
                "dense_fallback_used_count": float(self._dense_retriever.fallback_used_count),
                "retrieval_depth_rank": _RETRIEVAL_DEPTH_RANK.get(
                    str(retrieval_depth or "").strip().lower(),
                    0.0,
                ),
                "paper_top_k": float(plan.paper_top_k),
                "section_top_k_per_paper": float(plan.section_top_k_per_paper),
                "dense_chunk_top_k": float(plan.dense_chunk_top_k),
                "candidate_pool_max": float(plan.candidate_pool_max),
                "rerank_top_k": float(plan.rerank_top_k),
            },
        )

        quality = evaluate_evidence_pack(pack)
        pack.diagnostics.update(
            {
                "paper_coverage_score": quality.paper_coverage_score,
                "section_match_score": quality.section_match_score,
                "content_type_match_score": quality.content_type_match_score,
                "evidence_relevance_score": quality.evidence_relevance_score,
                "citation_support_score": quality.citation_support_score,
            }
        )
        return pack

    def _retrieve_section_candidates(
        self,
        query: str,
        paper_ids: set[str],
        dense_candidates: list[EvidenceCandidate],
        section_top_k_per_paper: int,
    ) -> list[EvidenceCandidate]:
        """Generate section-level candidates anchored to the identified paper set.

        Uses batch search to avoid N+1 per-paper queries.
        """
        if not paper_ids and not dense_candidates:
            return []

        dense_paper_ids = {c.paper_id for c in dense_candidates[:20] if c.paper_id}
        all_paper_ids = paper_ids | dense_paper_ids

        # Batch search: single pass over all papers instead of per-paper loop
        sections_by_paper = self._section_index.search_for_papers(
            all_paper_ids,
            query=query,
            top_k_per_paper=section_top_k_per_paper,
        )

        section_candidates: list[EvidenceCandidate] = []
        for pid, sections in sections_by_paper.items():
            for sec in sections:
                for chunk_id in sec.source_chunk_ids[:3]:
                    section_candidates.append(
                        EvidenceCandidate(
                            source_chunk_id=chunk_id,
                            paper_id=sec.paper_id,
                            section_id=sec.section_id,
                            content_type="text",
                            anchor_text=sec.section_summary[:200],
                            candidate_sources=["section"],
                        )
                    )
        return section_candidates

    def _retrieve_tree_candidates(
        self,
        *,
        query: str,
        paper_ids: list[str] | None,
        user_id: str = "",
    ) -> list[EvidenceCandidate]:
        """Retrieve RAPTOR tree-level candidates for multi-granularity search.

        Returns empty list if RAPTOR is disabled, tree index is not configured,
        or search times out.
        """
        if not RAPTOR_ENABLED:
            return []
        if not self._raptor_tree_index or not self._embedding_provider:
            return []
        if not user_id:
            logger.debug("RAPTOR tree search skipped: user_id is required for tenant isolation")
            return []

        try:
            start = time.monotonic()
            query_embedding = self._embedding_provider.embed_texts([query])[0]
            hits = self._raptor_tree_index.search(
                query_embedding=query_embedding,
                user_id=user_id,
                paper_ids=paper_ids,
                top_k=10,
            )

            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > RAPTOR_SEARCH_TIMEOUT_MS:
                logger.warning(
                    "RAPTOR tree search exceeded timeout",
                    elapsed_ms=round(elapsed_ms, 1),
                    timeout_ms=RAPTOR_SEARCH_TIMEOUT_MS,
                )
                return []

            candidates = []
            for hit in hits:
                candidates.append(
                    EvidenceCandidate(
                        source_chunk_id=hit.get("node_id", ""),
                        paper_id=hit.get("paper_id", ""),
                        section_id=f"raptor-L{hit.get('level', 0)}",
                        content_type="text",
                        anchor_text=hit.get("text", "")[:300],
                        candidate_sources=["raptor_tree"],
                        dense_score=float(hit.get("score", 0.0)),
                    )
                )
            return candidates

        except Exception as exc:
            logger.debug("RAPTOR tree search failed, degrading to chunk-only", error=str(exc))
            return []

    @staticmethod
    def _compute_paper_hit_rate(candidates: list[EvidenceCandidate]) -> float:
        if not candidates:
            return 0.0
        papers = {c.paper_id for c in candidates[:10] if c.paper_id}
        return round(min(len(papers) / max(len(candidates[:10]), 1), 1.0), 4)

    @staticmethod
    def _compute_section_diversity(candidates: list[EvidenceCandidate]) -> float:
        if not candidates:
            return 0.0
        sections = {c.section_id for c in candidates[:10] if c.section_id}
        return round(min(len(sections) / 5.0, 1.0), 4)


_default_retriever = HierarchicalRetriever()


def retrieve_evidence(query: str, query_family: str, stage: str, top_k: int = 10, user_id: str = "") -> EvidencePack:
    return _default_retriever.retrieve_evidence(
        query=query,
        query_family=query_family,
        stage=stage,
        top_k=top_k,
        user_id=user_id,
    )
