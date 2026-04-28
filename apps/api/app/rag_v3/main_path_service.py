from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Any
from uuid import uuid4

from pymilvus import connections

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.evidence_quality import score_evidence
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from app.rag_v3.schemas import EvidencePack
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)

ARTIFACT_ROOT = "artifacts/papers"
COLLECTION_SUFFIX = "v2_3"
EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"

COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}


def _safe_stage(stage: str) -> str:
    return stage if stage in COLLECTIONS else "rule"


@lru_cache(maxsize=3)
def _get_retriever(stage: str) -> HierarchicalRetriever:
    stage = _safe_stage(stage)
    settings = get_settings()
    paper_index, section_index = build_indexes_from_artifacts(artifact_root=ARTIFACT_ROOT, stage=stage)

    alias = f"v3_main_{stage}"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)

    provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)
    dense = DenseEvidenceRetriever(
        embedding_provider=provider,
        collection_name=COLLECTIONS[stage],
        milvus_alias=alias,
        output_fields=["source_chunk_id", "paper_id", "normalized_section_path", "content_type", "anchor_text"],
    )

    return HierarchicalRetriever(
        paper_index=paper_index,
        section_index=section_index,
        dense_retriever=dense,
    )


def retrieve_evidence(
    query: str,
    user_id: str,
    kb_id: str | None = None,
    paper_scope: list[str] | None = None,
    query_family: str | None = None,
    stage: str = "rule",
    trace_id: str | None = None,
    top_k: int = 10,
    section_paths: list[str] | None = None,
    page_from: int | None = None,
    page_to: int | None = None,
    content_types: list[str] | None = None,
) -> EvidencePack:
    _ = (user_id, kb_id)
    stage = _safe_stage(stage)
    family = query_family or "fact"
    retriever = _get_retriever(stage)
    pack = retriever.retrieve_evidence(
        query=query,
        query_family=family,
        stage=stage,
        top_k=top_k,
        section_paths=section_paths,
        page_from=page_from,
        page_to=page_to,
        content_types=content_types,
    )

    if paper_scope:
        allowed_papers = {p for p in paper_scope if p}
        filtered_candidates = [c for c in pack.candidates if c.paper_id in allowed_papers]
        pack = pack.model_copy(
            update={
                "candidates": filtered_candidates,
                "diagnostics": {
                    **pack.diagnostics,
                    "paper_scope_filter_applied": 1.0,
                    "paper_scope_filter_size": float(len(allowed_papers)),
                },
            }
        )

    if kb_id:
        pack = pack.model_copy(
            update={
                "diagnostics": {
                    **pack.diagnostics,
                    "kb_scope_requested": 1.0,
                }
            }
        )

    return pack


def build_answer_contract_payload(
    *,
    query: str,
    user_id: str,
    kb_id: str | None = None,
    paper_scope: list[str] | None = None,
    query_family: str | None = None,
    stage: str = "rule",
    trace_id: str | None = None,
    run_id: str | None = None,
    top_k: int = 10,
    section_paths: list[str] | None = None,
    page_from: int | None = None,
    page_to: int | None = None,
    content_types: list[str] | None = None,
) -> dict[str, Any]:
    trace = trace_id or str(uuid4())
    run = run_id or str(uuid4())
    settings = get_settings()

    t0 = perf_counter()
    pack = retrieve_evidence(
        query=query,
        user_id=user_id,
        kb_id=kb_id,
        paper_scope=paper_scope,
        query_family=query_family,
        stage=stage,
        trace_id=trace,
        top_k=top_k,
        section_paths=section_paths,
        page_from=page_from,
        page_to=page_to,
        content_types=content_types,
    )
    t1 = perf_counter()

    quality = score_evidence(pack)
    t2 = perf_counter()
    contract = build_answer_contract(pack, quality)
    t3 = perf_counter()

    citations: list[dict[str, Any]] = []
    evidence_blocks: list[dict[str, Any]] = []
    for cand in pack.candidates[:top_k]:
        source_payload = get_evidence_source_payload(cand.source_chunk_id) or {}
        citation_jump_url = source_payload.get("citation_jump_url") or build_citation_jump_url(
            paper_id=cand.paper_id,
            source_chunk_id=cand.source_chunk_id,
        )
        page_num = source_payload.get("page_num")
        section_path = source_payload.get("section_path") or cand.section_id
        support_status = next(
            (
                claim.support_status
                for claim in contract.claims
                if cand.source_chunk_id in claim.supporting_source_chunk_ids
            ),
            None,
        )
        text = source_payload.get("content") or cand.anchor_text
        citation = {
            "paper_id": cand.paper_id,
            "source_chunk_id": cand.source_chunk_id,
            "page_num": page_num,
            "section_path": section_path,
            "title": cand.paper_id,
            "anchor_text": cand.anchor_text,
            "text_preview": text[:300],
            "content_type": cand.content_type,
            "score": cand.rerank_score,
            "citation_jump_url": citation_jump_url,
        }
        citations.append(citation)
        evidence_blocks.append(
            {
                "evidence_id": cand.source_chunk_id,
                "source_type": "paper",
                "source_chunk_id": cand.source_chunk_id,
                "paper_id": cand.paper_id,
                "page_num": page_num,
                "section_path": section_path,
                "content_type": cand.content_type,
                "text": text,
                "score": cand.rerank_score,
                "rerank_score": cand.rerank_score,
                "support_status": support_status,
                "citation_jump_url": citation_jump_url,
            }
        )

    answer_text = "\n".join([c.get("anchor_text") or "" for c in citations[:3]]).strip()
    if not answer_text:
        answer_text = "Insufficient evidence to answer confidently."

    fallback_used = bool(pack.diagnostics.get("dense_fallback_used", 0.0) > 0)
    error_state = None
    if contract.answer_mode == "abstain":
        error_state = "abstain"
    elif fallback_used:
        error_state = "fallback_used"
    elif contract.answer_mode == "partial":
        error_state = "partial_answer"

    candidate_count = len(pack.candidates)
    paper_ids = {c.paper_id for c in pack.candidates if c.paper_id}
    section_ids = {c.section_id for c in pack.candidates if c.section_id}

    retrieval_latency_ms = (t1 - t0) * 1000.0
    evaluator_latency_ms = (t2 - t1) * 1000.0
    answer_latency_ms = (t3 - t2) * 1000.0
    total_latency_ms = (t3 - t0) * 1000.0

    trace_payload = {
        "trace_id": trace,
        "run_id": run,
        "runtime_profile": settings.RUNTIME_PROFILE,
        "query_family": query_family or "fact",
        "paper_candidate_count": len(paper_ids),
        "section_candidate_count": len(section_ids),
        "candidate_pool_size": candidate_count,
        "rerank_latency_ms": round(retrieval_latency_ms, 3),
        "llm_latency_ms": 0.0,
        "total_latency_ms": round(total_latency_ms, 3),
        "fallback_used": fallback_used,
        "fallback_reason": "unsupported_field_type" if fallback_used else None,
        "cost_estimate": round(candidate_count * 0.00002, 6),
        "answer_mode": contract.answer_mode,
        "error_state": error_state,
        "spans": {
            "rag.request": round(total_latency_ms, 3),
            "rag.query_planner": 0.0,
            "rag.paper_recall": 0.0,
            "rag.section_recall": 0.0,
            "rag.evidence_recall_dense": round(retrieval_latency_ms, 3),
            "rag.candidate_fusion": 0.0,
            "rag.rerank": 0.0,
            "rag.evidence_evaluator": round(evaluator_latency_ms, 3),
            "rag.answer_generation": round(answer_latency_ms, 3),
            "rag.citation_verification": 0.0,
        },
    }

    return {
        "response_type": "rag",
        "answer_mode": contract.answer_mode,
        "answer": answer_text,
        "claims": [c.model_dump() for c in contract.claims],
        "unsupported_claims": contract.unsupported_claims,
        "missing_evidence": contract.missing_evidence,
        "citations": citations,
        "evidence_blocks": evidence_blocks,
        "quality": {
            "citation_coverage": quality.citation_support_score,
            "unsupported_claim_rate": len(contract.unsupported_claims) / max(len(contract.claims), 1),
            "answer_evidence_consistency": quality.evidence_relevance_score,
            "fallback_used": fallback_used,
            "fallback_reason": "unsupported_field_type" if fallback_used else None,
        },
        "trace": trace_payload,
        "trace_id": trace,
        "run_id": run,
        "retrieval_trace_id": trace,
        "cost_estimate": trace_payload["cost_estimate"],
        "error_state": error_state,
    }
