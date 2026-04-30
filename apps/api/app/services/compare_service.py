"""compare_service.py – Phase 4 evidence-backed multi-paper compare.

Responsibilities:
1. Receive paper_ids + dimensions + question.
2. Run HybridRetriever to get per-paper evidence candidates.
3. Map each (paper_id, dimension) → best evidence cell.
4. Build CompareMatrix with explicit unsupported markers.
5. Return AnswerContract(response_type="compare", compare_matrix=…).

This service does NOT call an LLM to generate free-form markdown tables.
All content is derived from evidence candidates; missing cells are
explicitly marked "not_enough_evidence".
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.core.rag_runtime_profile import (
    get_active_rag_runtime_profile,
    get_collection_for_stage,
    get_embedding_model_for_query_family,
)
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hybrid_retriever import HybridRetriever
from app.rag_v3.retrieval.sparse_evidence_retriever import SparseEvidenceRetriever
from app.rag_v3.schemas import (
    AnswerContract,
    AnswerClaim,
    AnswerCitation,
    CompareCell,
    CompareDimension,
    CompareMatrix,
    CompareRow,
    CrossPaperInsight,
    EvidenceBlock,
    EvidenceCandidate,
    EvidencePack,
)
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.services.phase_i_routing_service import get_phase_i_routing_service
from app.services.truthfulness_service import get_truthfulness_service

COMPARE_STAGE = "rule"
RUNTIME_PROFILE = get_active_rag_runtime_profile()

# ---------------------------------------------------------------------------
# Default dimension catalogue for compare matrix
# ---------------------------------------------------------------------------

DEFAULT_DIMENSIONS: list[dict[str, str]] = [
    {"id": "problem", "label": "Research Problem"},
    {"id": "method", "label": "Method"},
    {"id": "dataset", "label": "Dataset"},
    {"id": "metrics", "label": "Metrics"},
    {"id": "results", "label": "Results"},
    {"id": "limitations", "label": "Limitations"},
    {"id": "innovation", "label": "Key Innovation"},
]

ALLOWED_DIMENSION_IDS = {d["id"] for d in DEFAULT_DIMENSIONS}

# Dimension → section-path hints to steer dense retrieval
_DIM_SECTION_HINTS: dict[str, list[str]] = {
    "problem": ["introduction", "abstract", "motivation"],
    "method": ["method", "methodology", "approach", "model"],
    "dataset": ["dataset", "data", "experiment", "evaluation"],
    "metrics": ["experiment", "evaluation", "metric", "result"],
    "results": ["result", "experiment", "evaluation", "finding"],
    "limitations": ["limitation", "future", "discussion"],
    "innovation": ["contribution", "introduction", "abstract"],
}


class _NoopSparseRetriever(SparseEvidenceRetriever):
    """Disable synthetic lexical placeholders on the production compare path."""

    def retrieve(self, query: str, top_k: int) -> list[EvidenceCandidate]:
        _ = (query, top_k)
        return []


@lru_cache(maxsize=1)
def get_compare_retriever() -> HybridRetriever:
    """Return the canonical compare retriever wired to the real dense index."""
    from pymilvus import connections

    settings = get_settings()
    alias = f"v3_compare_{COMPARE_STAGE}"
    connections.connect(
        alias=alias,
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )

    provider = create_embedding_provider(
        RUNTIME_PROFILE.embedding_provider,
        get_embedding_model_for_query_family("compare"),
    )
    dense = DenseEvidenceRetriever(
        embedding_provider=provider,
        collection_name=get_collection_for_stage(COMPARE_STAGE),
        milvus_alias=alias,
        output_fields=[
            "source_chunk_id",
            "paper_id",
            "normalized_section_path",
            "content_type",
            "anchor_text",
            "page_num",
        ],
    )

    return HybridRetriever(
        dense_retriever=dense,
        sparse_retriever=_NoopSparseRetriever(),
    )


def _candidate_to_evidence_block(cand: EvidenceCandidate) -> EvidenceBlock:
    source_payload = get_evidence_source_payload(cand.source_chunk_id) or {}
    citation_jump_url = source_payload.get("citation_jump_url") or build_citation_jump_url(
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
    )
    return EvidenceBlock(
        evidence_id=cand.source_chunk_id,
        source_type="paper",
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
        page_num=source_payload.get("page_num"),
        section_path=source_payload.get("section_path") or cand.section_id or None,
        content_type=cand.content_type,
        text=cand.anchor_text,
        score=cand.rrf_score,
        rerank_score=cand.rerank_score,
        support_status=(
            "supported" if cand.rerank_score >= 0.7
            else "partially_supported" if cand.rerank_score >= 0.4
            else "unsupported"
        ),
        citation_jump_url=citation_jump_url,
    )


def _fill_cell(
    dimension_id: str,
    paper_id: str,
    candidates: list[EvidenceCandidate],
) -> CompareCell:
    """Pick the best candidate for a (dimension, paper) cell.

    A candidate is considered relevant if its section_id or anchor_text
    contains any of the dimension's section hints.  If none found, the
    cell is marked not_enough_evidence.
    """
    hints = _DIM_SECTION_HINTS.get(dimension_id, [dimension_id])
    scored: list[tuple[float, EvidenceCandidate]] = []
    for cand in candidates:
        if cand.paper_id != paper_id:
            continue
        section_text = (cand.section_id or "").lower()
        anchor_text = (cand.anchor_text or "").lower()
        # Soft match: score by hint overlap
        hint_score = sum(
            1 for h in hints if h in section_text or h in anchor_text
        )
        total_score = hint_score * 0.5 + cand.rerank_score
        scored.append((total_score, cand))

    if not scored:
        return CompareCell(
            dimension_id=dimension_id,
            content="",
            support_status="not_enough_evidence",
            evidence_blocks=[],
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    best_cand = scored[0][1]
    block = _candidate_to_evidence_block(best_cand)

    support_status = (
        "supported" if best_cand.rerank_score >= 0.7
        else "partially_supported" if best_cand.rerank_score >= 0.4
        else "unsupported"
    )

    return CompareCell(
        dimension_id=dimension_id,
        content=best_cand.anchor_text or "",
        support_status=support_status,
        evidence_blocks=[block],
    )


def build_compare_matrix(
    *,
    paper_ids: list[str],
    paper_meta: dict[str, dict[str, Any]],  # paper_id -> {title, year}
    pack: EvidencePack,
    dimensions: list[CompareDimension],
) -> CompareMatrix:
    """Build the evidence-backed compare matrix from an EvidencePack.

    Parameters
    ----------
    paper_ids: ordered list of paper IDs.
    paper_meta: title/year keyed by paper_id.
    pack: EvidencePack from HybridRetriever.
    dimensions: list of dimensions to fill.
    """
    candidates = pack.candidates

    rows: list[CompareRow] = []
    for pid in paper_ids:
        meta = paper_meta.get(pid, {})
        cells = [_fill_cell(dim.id, pid, candidates) for dim in dimensions]
        rows.append(
            CompareRow(
                paper_id=pid,
                title=meta.get("title", pid),
                year=meta.get("year"),
                cells=cells,
            )
        )

    # Cross-paper insights: candidates supported by multiple papers
    cross_by_dim: dict[str, list[EvidenceCandidate]] = {}
    for cand in candidates:
        for dim in dimensions:
            hints = _DIM_SECTION_HINTS.get(dim.id, [])
            if any(h in (cand.section_id or "").lower() or h in (cand.anchor_text or "").lower() for h in hints):
                cross_by_dim.setdefault(dim.id, []).append(cand)

    insights: list[CrossPaperInsight] = []
    for dim_id, cands in cross_by_dim.items():
        involved_papers = list(dict.fromkeys(c.paper_id for c in cands))
        if len(involved_papers) < 2:
            continue
        evidence_blocks = [_candidate_to_evidence_block(c) for c in cands[:3]]
        dim_label = next((d.label for d in dimensions if d.id == dim_id), dim_id)
        insights.append(
            CrossPaperInsight(
                claim=f"Cross-paper evidence for dimension: {dim_label}",
                supporting_paper_ids=involved_papers,
                evidence_blocks=evidence_blocks,
            )
        )

    return CompareMatrix(
        paper_ids=paper_ids,
        dimensions=dimensions,
        rows=rows,
        summary="",
        cross_paper_insights=insights,
    )


def _build_truthfulness_text(
    *,
    matrix: CompareMatrix,
    paper_meta: dict[str, dict[str, Any]],
) -> str:
    dimension_labels = {dimension.id: dimension.label for dimension in matrix.dimensions}
    sentences: list[str] = []

    for row in matrix.rows:
        paper_title = str(paper_meta.get(row.paper_id, {}).get("title") or row.title or row.paper_id)
        for cell in row.cells:
            if not cell.content or cell.support_status == "not_enough_evidence":
                continue
            dimension_label = dimension_labels.get(cell.dimension_id, cell.dimension_id)
            sentences.append(f"{paper_title} {dimension_label}: {cell.content}.")

    for insight in matrix.cross_paper_insights:
        if not insight.claim:
            continue
        sentences.append(f"{insight.claim}.")

    return " ".join(sentences).strip()


def _resolve_compare_answer_mode(
    *,
    truthfulness_claims: list[dict[str, Any]],
    fallback_mode: str,
) -> str:
    if not truthfulness_claims:
        return fallback_mode

    supported = sum(1 for claim in truthfulness_claims if claim.get("support_status") == "supported")
    unsupported = sum(1 for claim in truthfulness_claims if claim.get("support_status") == "unsupported")
    total = len(truthfulness_claims)

    if supported == total:
        return "full"
    if unsupported == total:
        return "abstain"
    return "partial"


def build_compare_contract(
    *,
    paper_ids: list[str],
    paper_meta: dict[str, dict[str, Any]],
    pack: EvidencePack,
    dimensions: list[CompareDimension],
    trace_id: str | None = None,
    run_id: str | None = None,
) -> AnswerContract:
    """Build a full AnswerContract with response_type='compare'."""
    routing = get_phase_i_routing_service().route(
        query=pack.query,
        query_family=pack.query_family,
        paper_scope=paper_ids,
    )
    matrix = build_compare_matrix(
        paper_ids=paper_ids,
        paper_meta=paper_meta,
        pack=pack,
        dimensions=dimensions,
    )

    all_blocks: list[EvidenceBlock] = [
        block
        for row in matrix.rows
        for cell in row.cells
        for block in cell.evidence_blocks
    ]
    # Deduplicate by evidence_id
    seen: set[str] = set()
    deduped_blocks: list[EvidenceBlock] = []
    for b in all_blocks:
        if b.evidence_id not in seen:
            seen.add(b.evidence_id)
            deduped_blocks.append(b)

    claims: list[AnswerClaim] = []
    citations: list[AnswerCitation] = []
    for block in deduped_blocks:
        claims.append(
            AnswerClaim(
                claim=block.text or block.source_chunk_id,
                support_status=block.support_status or "unsupported",
                supporting_source_chunk_ids=[block.source_chunk_id],
            )
        )
        citations.append(
            AnswerCitation(
                paper_id=block.paper_id,
                source_chunk_id=block.source_chunk_id,
                page_num=block.page_num,
                section_path=block.section_path,
                score=block.rerank_score,
                content_type=block.content_type,
                citation_jump_url=block.citation_jump_url,
            )
        )

    total = len(claims)
    supported = sum(1 for c in claims if c.support_status == "supported")
    answer_mode = (
        "full" if total > 0 and supported / total >= 0.8
        else "partial" if total > 0
        else "abstain"
    )
    truthfulness_text = _build_truthfulness_text(matrix=matrix, paper_meta=paper_meta)
    truthfulness_report = get_truthfulness_service().evaluate_text(
        text=truthfulness_text,
        evidence_blocks=deduped_blocks,
    )
    claim_rows = get_truthfulness_service().report_to_answer_claims(truthfulness_report)
    resolved_answer_mode = _resolve_compare_answer_mode(
        truthfulness_claims=claim_rows,
        fallback_mode=answer_mode,
    )
    truthfulness_summary = {
        **truthfulness_report.get("summary", {}),
        "citation_coverage": supported / max(total, 1),
        "answer_mode": resolved_answer_mode,
    }

    return AnswerContract(
        response_type="compare",
        answer_mode=resolved_answer_mode,
        answer="",
        claims=claim_rows,
        citations=citations,
        evidence_blocks=deduped_blocks,
        quality={
            "citation_coverage": supported / max(total, 1),
            "fallback_used": False,
            "fallback_reason": None,
        },
        trace_id=trace_id or uuid4().hex,
        run_id=run_id or uuid4().hex,
        compare_matrix=matrix,
        task_family=routing.task_family,
        execution_mode=routing.execution_mode,
        truthfulness_required=routing.truthfulness_required,
        truthfulness_summary=truthfulness_summary,
        truthfulness_report=truthfulness_report,
        retrieval_plane_policy=routing.retrieval_plane_policy,
    )
