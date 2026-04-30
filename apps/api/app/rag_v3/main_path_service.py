from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.core.rag_runtime_profile import (
    get_active_rag_runtime_profile,
    get_collection_for_stage,
    get_embedding_model_for_policy,
)
from app.core.runtime_contract import build_online_binding, build_vector_store_binding
from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.evidence_quality import score_evidence
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.rerank.qwen3vl_rerank_adapter import get_rerank_runtime_binding
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from app.rag_v3.schemas import EvidenceBlock, EvidencePack
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.services.phase_i_routing_service import get_phase_i_routing_service
from app.services.truthfulness_service import get_truthfulness_service

ARTIFACT_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "papers"
RUNTIME_PROFILE = get_active_rag_runtime_profile()


def _safe_stage(stage: str) -> str:
    return stage if stage in RUNTIME_PROFILE.collections else "rule"


def _provider_runtime_truth(provider: Any, *, requested_mode: str, model: str) -> dict[str, Any]:
    if hasattr(provider, "get_runtime_binding"):
        return provider.get_runtime_binding().to_dict()
    return build_online_binding(
        component="embedding",
        provider_name=RUNTIME_PROFILE.embedding_provider,
        model=model,
        dimension=getattr(provider, "dim", None),
        supports_multimodal=False,
        requested_mode=requested_mode,  # type: ignore[arg-type]
    ).to_dict()


def _merge_runtime_modes(modes: list[str]) -> str:
    unique_modes = {mode for mode in modes if mode}
    if not unique_modes:
        return "online"
    if len(unique_modes) == 1:
        return next(iter(unique_modes))
    if "shim" in unique_modes:
        return "mixed"
    if "lite" in unique_modes:
        return "mixed"
    if "local" in unique_modes:
        return "mixed"
    return "mixed"


def _collect_runtime_events(bindings: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    degraded_conditions: list[str] = []
    fallback_events: list[str] = []
    for binding in bindings:
        for condition in binding.get("degraded_conditions", []):
            if condition and condition not in degraded_conditions:
                degraded_conditions.append(condition)
        resolved_mode = str(binding.get("resolved_mode") or "")
        if resolved_mode == "shim" and "shim_provider_fallback" not in fallback_events:
            fallback_events.append("shim_provider_fallback")
        if resolved_mode == "local" and "local_model_fallback" not in fallback_events:
            fallback_events.append("local_model_fallback")
        if resolved_mode == "lite" and "milvus_lite_fallback" not in fallback_events:
            fallback_events.append("milvus_lite_fallback")
    return degraded_conditions, fallback_events


@lru_cache(maxsize=3)
def _get_retriever(stage: str, embedding_model: str) -> HierarchicalRetriever:
    from pymilvus import connections

    stage = _safe_stage(stage)
    settings = get_settings()
    paper_index, section_index = build_indexes_from_artifacts(artifact_root=ARTIFACT_ROOT, stage=stage)

    alias = f"v3_main_{stage}_{embedding_model}"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)

    provider = create_embedding_provider(RUNTIME_PROFILE.embedding_provider, embedding_model)
    dense = DenseEvidenceRetriever(
        embedding_provider=provider,
        collection_name=get_collection_for_stage(stage),
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
    retrieval_depth: str | None = None,
    retrieval_model_policy: str | None = None,
    section_paths: list[str] | None = None,
    page_from: int | None = None,
    page_to: int | None = None,
    content_types: list[str] | None = None,
) -> EvidencePack:
    _ = (user_id, kb_id)
    settings = get_settings()
    stage = _safe_stage(stage)
    family = query_family or "fact"
    resolved_model_policy = retrieval_model_policy or (
        "pro" if family in {"compare", "cross_paper", "survey", "related_work", "method_evolution", "conflicting_evidence", "hard"} else "flash"
    )
    embedding_model = get_embedding_model_for_policy(
        resolved_model_policy,
        query_family=family,
    )
    retriever = _get_retriever(stage, embedding_model)
    pack = retriever.retrieve_evidence(
        query=query,
        query_family=family,
        stage=stage,
        top_k=top_k,
        retrieval_depth=retrieval_depth,
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

    provider = create_embedding_provider(RUNTIME_PROFILE.embedding_provider, embedding_model)
    vector_binding = build_vector_store_binding(
        backend=RUNTIME_PROFILE.vector_store_backend,
        resolved_mode="online",
        requested_mode=settings.RUNTIME_MODE,  # type: ignore[arg-type]
    )
    generation_binding = build_online_binding(
        component="generation",
        provider_name=RUNTIME_PROFILE.llm_provider,
        model=RUNTIME_PROFILE.llm_model,
        dimension=None,
        supports_multimodal=None,
        requested_mode=settings.RUNTIME_MODE,  # type: ignore[arg-type]
    )
    embedding_binding = _provider_runtime_truth(
        provider,
        requested_mode=settings.RUNTIME_MODE,
        model=embedding_model,
    )
    rerank_binding = get_rerank_runtime_binding().to_dict()
    vector_store_binding = vector_binding.to_dict()
    generation_runtime_binding = generation_binding.to_dict()
    retrieval_plane_mode = _merge_runtime_modes(
        [
            str(embedding_binding.get("resolved_mode") or ""),
            str(rerank_binding.get("resolved_mode") or ""),
            str(vector_store_binding.get("resolved_mode") or ""),
        ]
    )
    generation_plane_mode = _merge_runtime_modes(
        [str(generation_runtime_binding.get("resolved_mode") or "")]
    )
    runtime_mode = _merge_runtime_modes([retrieval_plane_mode, generation_plane_mode])
    degraded_conditions, fallback_events = _collect_runtime_events(
        [embedding_binding, rerank_binding, vector_store_binding, generation_runtime_binding]
    )
    pack = pack.model_copy(
        update={
            "diagnostics": {
                **pack.diagnostics,
                "runtime_truth": {
                    "runtime_profile": RUNTIME_PROFILE.name,
                    "requested_runtime_mode": settings.RUNTIME_MODE,
                    "runtime_mode": runtime_mode,
                    "retrieval_plane_mode": retrieval_plane_mode,
                    "generation_plane_mode": generation_plane_mode,
                    "fallback_events": fallback_events,
                    "degraded_conditions": degraded_conditions,
                    "query_family": family,
                    "requested_retrieval_depth": retrieval_depth or "",
                    "requested_retrieval_model_policy": retrieval_model_policy or "",
                    "resolved_retrieval_model_policy": resolved_model_policy,
                    "resolved_embedding_model": embedding_model,
                    "vector_collection": get_collection_for_stage(stage),
                    "embedding": embedding_binding,
                    "rerank": rerank_binding,
                    "vector_store": vector_store_binding,
                    "generation": generation_runtime_binding,
                },
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
    routing = get_phase_i_routing_service().route(
        query=query,
        query_family=query_family,
        paper_scope=paper_scope,
    )

    t0 = perf_counter()
    pack = retrieve_evidence(
        query=query,
        user_id=user_id,
        kb_id=kb_id,
        paper_scope=paper_scope,
        query_family=routing.query_family,
        stage=stage,
        trace_id=trace,
        top_k=top_k,
        retrieval_depth=routing.retrieval_depth,
        retrieval_model_policy=routing.retrieval_model_policy,
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
    typed_blocks = [EvidenceBlock.model_validate(block) for block in evidence_blocks]
    truthfulness_report = get_truthfulness_service().evaluate_text(
        text=answer_text,
        evidence_blocks=typed_blocks,
    )
    answer_mode = truthfulness_report.get("answerMode") or contract.answer_mode
    claims = get_truthfulness_service().report_to_answer_claims(truthfulness_report)

    fallback_used = bool(pack.diagnostics.get("dense_fallback_used", 0.0) > 0)
    runtime_truth = pack.diagnostics.get("runtime_truth", {})
    error_state = None
    if answer_mode == "abstain":
        error_state = "abstain"
    elif fallback_used:
        error_state = "fallback_used"
    elif answer_mode == "partial":
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
        "runtime_profile": RUNTIME_PROFILE.name,
        "runtime_mode": runtime_truth.get("runtime_mode", settings.RUNTIME_MODE),
        "retrieval_plane_mode": runtime_truth.get("retrieval_plane_mode", "online"),
        "generation_plane_mode": runtime_truth.get("generation_plane_mode", "online"),
        "query_family": routing.query_family,
        "paper_candidate_count": len(paper_ids),
        "section_candidate_count": len(section_ids),
        "candidate_pool_size": candidate_count,
        "rerank_latency_ms": round(retrieval_latency_ms, 3),
        "llm_latency_ms": 0.0,
        "total_latency_ms": round(total_latency_ms, 3),
        "fallback_used": fallback_used,
        "fallback_reason": "unsupported_field_type" if fallback_used else None,
        "fallback_events": runtime_truth.get("fallback_events", []),
        "degraded_conditions": runtime_truth.get("degraded_conditions", []),
        "cost_estimate": round(candidate_count * 0.00002, 6),
        "answer_mode": answer_mode,
        "error_state": error_state,
        "task_family": routing.task_family,
        "execution_mode": routing.execution_mode,
        "truthfulness_required": routing.truthfulness_required,
        "truthfulness_report_summary": truthfulness_report.get("summary", {}),
        "retrieval_plane_policy": routing.retrieval_plane_policy,
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
        "answer_mode": answer_mode,
        "answer": answer_text,
        "claims": claims,
        "unsupported_claims": [
            item.get("text", "")
            for item in truthfulness_report.get("results", [])
            if item.get("support_level") == "unsupported"
        ],
        "missing_evidence": contract.missing_evidence,
        "citations": citations,
        "evidence_blocks": evidence_blocks,
        "quality": {
            "citation_coverage": quality.citation_support_score,
            "unsupported_claim_rate": truthfulness_report.get("unsupportedClaimRate", 0.0),
            "answer_evidence_consistency": quality.evidence_relevance_score,
            "fallback_used": fallback_used,
            "fallback_reason": "unsupported_field_type" if fallback_used else None,
        },
        "trace": trace_payload,
        "trace_id": trace,
        "run_id": run,
        "retrieval_trace_id": trace,
        "runtime_truth": runtime_truth,
        "cost_estimate": trace_payload["cost_estimate"],
        "error_state": error_state,
        "task_family": routing.task_family,
        "execution_mode": routing.execution_mode,
        "truthfulness_required": routing.truthfulness_required,
        "truthfulness_summary": truthfulness_report.get("summary", {}),
        "truthfulness_report": truthfulness_report,
        "retrieval_plane_policy": routing.retrieval_plane_policy,
        "degraded_conditions": runtime_truth.get("degraded_conditions", []),
    }
