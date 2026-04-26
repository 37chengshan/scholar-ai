from __future__ import annotations

from dataclasses import dataclass

from app.rag_v3.planner.query_family_router import infer_query_family, normalize_query_family


@dataclass(frozen=True)
class QueryPlan:
    query: str
    query_family: str
    paper_top_k: int
    section_top_k_per_paper: int
    dense_chunk_top_k: int
    lexical_chunk_top_k: int
    numeric_top_k: int
    caption_top_k: int
    graph_top_k: int
    candidate_pool_max: int
    rerank_top_k: int


def build_query_plan(query: str, query_family: str | None = None) -> QueryPlan:
    family = normalize_query_family(query_family) if query_family else infer_query_family(query)

    paper_top_k = 12
    section_top_k_per_paper = 5
    dense_chunk_top_k = 120
    lexical_chunk_top_k = 120
    numeric_top_k = 50
    caption_top_k = 50
    graph_top_k = 50
    candidate_pool_max = 180
    rerank_top_k = 10

    if family in {"compare", "cross_paper", "survey", "related_work", "method_evolution", "conflicting_evidence"}:
        graph_top_k = 80
    if family in {"table", "figure"}:
        caption_top_k = 80
    if family == "numeric":
        numeric_top_k = 80

    return QueryPlan(
        query=query,
        query_family=family,
        paper_top_k=paper_top_k,
        section_top_k_per_paper=section_top_k_per_paper,
        dense_chunk_top_k=dense_chunk_top_k,
        lexical_chunk_top_k=lexical_chunk_top_k,
        numeric_top_k=numeric_top_k,
        caption_top_k=caption_top_k,
        graph_top_k=graph_top_k,
        candidate_pool_max=candidate_pool_max,
        rerank_top_k=rerank_top_k,
    )
