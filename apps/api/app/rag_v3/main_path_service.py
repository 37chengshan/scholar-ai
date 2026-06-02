"""Main path RAG service: orchestrates retrieval, evidence scoring, and answer generation.

Refactored into sub-modules:
- prompt_builder.py: prompt assembly and text cleaning
- display_selector.py: display mode selection and query classification
- runtime_binding.py: retriever initialization and runtime binding
"""

from __future__ import annotations

import asyncio
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.core.vector_store_repository import get_vector_store_repository
from app.models.retrieval import SearchConstraints
from app.core.rag_runtime_profile import (
    get_collection_for_stage,
    get_embedding_model_for_policy,
)
from app.core.runtime_contract import build_online_binding, build_vector_store_binding
from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.evidence_quality import score_evidence
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.rerank.qwen3vl_rerank_adapter import get_rerank_runtime_binding
from app.rag_v3.schemas import EvidenceBlock, EvidenceCandidate, EvidencePack
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.services.phase_i_routing_service import get_phase_i_routing_service
from app.services.truthfulness_service import get_truthfulness_service
from app.services.evidence_action_service import build_recovery_actions
from app.services.phase6_runtime_service import build_phase6_runtime_contract

# Imported from extracted modules
from app.rag_v3.runtime_binding import (
    ARTIFACT_ROOT,
    RUNTIME_PROFILE,
    safe_stage,
    get_retriever,
    provider_runtime_truth,
    merge_runtime_modes,
    collect_runtime_events,
    resolve_runtime_execution_mode,
)
from app.rag_v3.display_selector import (
    normalize_query_text,
    is_summary_seeking_query,
    is_compare_family,
    should_merge_summary_candidates,
    is_summary_candidate,
    select_display_candidates,
)
from app.rag_v3.prompt_builder import (
    clean_display_evidence_text,
    build_summary_display_text,
    generate_answer_from_citations,
)
from app.rag_v3.evidence_helpers import (
    normalize_handoff_evidence_rows,
    load_paper_display_title_map,
    build_summary_record_map,
    append_abstain_scope_fallback,
)

# Re-export for backward compatibility
_clean_display_evidence_text = clean_display_evidence_text
_build_summary_display_text = build_summary_display_text


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
    _ = kb_id
    settings = get_settings()
    stage = safe_stage(stage)
    family = query_family or "fact"
    resolved_model_policy = retrieval_model_policy or (
        "pro" if family in {"compare", "cross_paper", "survey", "related_work", "method_evolution", "conflicting_evidence", "hard"} else "flash"
    )
    embedding_model = get_embedding_model_for_policy(
        resolved_model_policy,
        query_family=family,
    )
    retriever = get_retriever(stage, embedding_model)
    pack = retriever.retrieve_evidence(
        query=query,
        query_family=family,
        stage=stage,
        top_k=top_k,
        paper_scope=paper_scope,
        retrieval_depth=retrieval_depth,
        section_paths=section_paths,
        page_from=page_from,
        page_to=page_to,
        content_types=content_types,
        user_id=user_id,
    )

    if paper_scope and should_merge_summary_candidates(query=query, query_family=family):
        summary_candidates = _retrieve_summary_index_candidates(
            query=query,
            user_id=user_id,
            paper_scope=paper_scope,
            embedding_model=embedding_model,
            top_k=max(top_k, 4),
        )
        if summary_candidates:
            merged_candidates = list(summary_candidates)
            seen_source_ids = {candidate.source_chunk_id for candidate in summary_candidates if candidate.source_chunk_id}
            for candidate in pack.candidates:
                if candidate.source_chunk_id and candidate.source_chunk_id in seen_source_ids:
                    continue
                seen_source_ids.add(candidate.source_chunk_id)
                merged_candidates.append(candidate)
            pack = pack.model_copy(
                update={
                    "candidates": merged_candidates,
                    "diagnostics": {
                        **pack.diagnostics,
                        "summary_index_hits": float(len(summary_candidates)),
                        "summary_index_used": 1.0,
                    },
                }
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
        requested_mode=settings.RUNTIME_MODE,
    )
    generation_binding = build_online_binding(
        component="generation",
        provider_name=RUNTIME_PROFILE.llm_provider,
        model=RUNTIME_PROFILE.llm_model,
        dimension=None,
        supports_multimodal=None,
        requested_mode=settings.RUNTIME_MODE,
    )
    embedding_binding = provider_runtime_truth(
        provider,
        requested_mode=settings.RUNTIME_MODE,
        model=embedding_model,
    )
    rerank_binding = get_rerank_runtime_binding().to_dict()
    vector_store_binding = vector_binding.to_dict()
    generation_runtime_binding = generation_binding.to_dict()
    retrieval_plane_mode = merge_runtime_modes(
        [
            str(embedding_binding.get("resolved_mode") or ""),
            str(rerank_binding.get("resolved_mode") or ""),
            str(vector_store_binding.get("resolved_mode") or ""),
        ]
    )
    generation_plane_mode = merge_runtime_modes(
        [str(generation_runtime_binding.get("resolved_mode") or "")]
    )
    runtime_mode = merge_runtime_modes([retrieval_plane_mode, generation_plane_mode])
    degraded_conditions, fallback_events = collect_runtime_events(
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


def _retrieve_summary_index_candidates(
    *,
    query: str,
    user_id: str,
    paper_scope: list[str],
    embedding_model: str,
    top_k: int,
) -> list[Any]:
    scoped_paper_ids = [paper_id for paper_id in dict.fromkeys(paper_scope) if paper_id]
    if not scoped_paper_ids:
        return []

    provider = create_embedding_provider(RUNTIME_PROFILE.embedding_provider, embedding_model)
    embedding = provider.embed_texts([query])[0]
    hits = get_vector_store_repository().search_summary_index(
        embedding=embedding,
        user_id=user_id,
        top_k=top_k,
        constraints=SearchConstraints(
            user_id=user_id,
            paper_ids=scoped_paper_ids,
            content_types=["text"],
            index_type="summary",
        ),
        summary_type="paper_summary",
    )

    candidates = []
    for hit in hits:
        if not hit.source_id or not hit.paper_id:
            continue
        canonical_source_chunk_id = (
            (hit.raw_data or {}).get("source_chunk_id")
            or (hit.raw_data or {}).get("chunk_id")
            or hit.source_id
        )
        canonical_source_chunk_id = str(canonical_source_chunk_id or "").strip()
        if not canonical_source_chunk_id:
            continue
        text = (hit.text or "")[:300]
        candidates.append(
            EvidenceCandidate(
                source_chunk_id=canonical_source_chunk_id,
                paper_id=str(hit.paper_id),
                section_id=str(hit.section or hit.section_path or "paper_summary"),
                content_type="text",
                anchor_text=text,
                candidate_sources=["summary_index"],
                dense_score=float(hit.score or 0.0),
                rrf_score=float(hit.score or 0.0),
                rerank_score=max(float(hit.score or 0.0), 0.75),
            )
        )
    return candidates


async def build_answer_contract_payload(
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
    handoff_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_query = normalize_query_text(query)
    trace = trace_id or str(uuid4())
    run = run_id or str(uuid4())
    settings = get_settings()
    routing = get_phase_i_routing_service().route(
        query=normalized_query,
        query_family=query_family,
        paper_scope=paper_scope,
    )
    resolved_execution_mode, execution_mode_degraded_conditions = resolve_runtime_execution_mode(
        requested_execution_mode=routing.execution_mode,
        paper_scope=paper_scope,
    )

    t0 = perf_counter()
    pack = retrieve_evidence(
        query=normalized_query,
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
    summary_query = is_summary_seeking_query(normalized_query)
    paper_title_map = await load_paper_display_title_map(user_id, paper_scope)
    normalized_handoff_evidence = normalize_handoff_evidence_rows(handoff_evidence)
    boosted_candidates = list(pack.candidates)
    if summary_query:
        boosted_candidates.sort(
            key=lambda cand: (
                1 if any(hint in (cand.section_id or "").lower() for hint in ("abstract", "introduction", "motivation", "contribution", "summary", "overview")) else 0,
                cand.rerank_score,
            ),
            reverse=True,
        )

    summary_records: list[dict[str, Any]] = []
    include_summary_records = bool(paper_scope) and (summary_query or is_compare_family(routing.query_family))
    if include_summary_records and paper_scope:
        paper_index, _ = build_indexes_from_artifacts(
            artifact_root=ARTIFACT_ROOT,
            stage=stage,
            paper_ids=paper_scope,
        )
        for paper_id in paper_scope:
            artifact = paper_index.get(paper_id)
            if artifact is None:
                continue
            summary_records.append(
                {
                    "paper_id": artifact.paper_id,
                    "title": paper_title_map.get(artifact.paper_id) or artifact.title or artifact.paper_id,
                    "abstract": artifact.abstract,
                    "paper_summary": artifact.paper_summary,
                    "method_summary": artifact.method_summary,
                    "result_summary": artifact.result_summary,
                    "representative_source_chunk_ids": list(artifact.representative_source_chunk_ids or []),
                }
            )
    if summary_query and not summary_records:
        seen_summary_papers: set[str] = set()
        for cand in boosted_candidates:
            if "summary_index" not in cand.candidate_sources:
                continue
            if not cand.paper_id or cand.paper_id in seen_summary_papers:
                continue
            seen_summary_papers.add(cand.paper_id)
            summary_records.append(
                {
                    "paper_id": cand.paper_id,
                    "title": paper_title_map.get(cand.paper_id) or cand.paper_id,
                    "abstract": "",
                    "paper_summary": cand.anchor_text,
                    "method_summary": "",
                    "result_summary": "",
                    "representative_source_chunk_ids": [cand.source_chunk_id] if cand.source_chunk_id else [],
                }
            )

    display_candidates = select_display_candidates(
        boosted_candidates,
        top_k=top_k,
        query_family=routing.query_family,
    )
    summary_record_map = build_summary_record_map(summary_records)

    handoff_display_rows: list[dict[str, Any]] = []
    if is_compare_family(routing.query_family) and normalized_handoff_evidence:
        seen_handoff_ids: set[str] = set()
        for row in normalized_handoff_evidence:
            source_chunk_id = row["source_chunk_id"]
            handoff_id = str(row.get("handoff_id") or "").strip() or (
                f'{row["paper_id"]}::{source_chunk_id}::{row.get("dimension_id") or ""}::{row.get("claim") or ""}'
            )
            if handoff_id in seen_handoff_ids:
                continue
            seen_handoff_ids.add(handoff_id)
            text = clean_display_evidence_text(
                str(row.get("text") or ""),
                title=row.get("title") or paper_title_map.get(row["paper_id"]),
            )
            if not text:
                continue
            handoff_display_rows.append(
                {
                    "handoff_id": handoff_id,
                    "paper_id": row["paper_id"],
                    "source_chunk_id": source_chunk_id,
                    "page_num": row.get("page_num"),
                    "section_path": row.get("section_path") or "compare_handoff",
                    "title": row.get("title") or paper_title_map.get(row["paper_id"]) or row["paper_id"],
                    "anchor_text": row.get("claim") or text[:200],
                    "text_preview": text[:300],
                    "content_type": row.get("content_type") or "text",
                    "score": 1.0,
                    "citation_jump_url": row.get("citation_jump_url")
                    or build_citation_jump_url(
                        paper_id=row["paper_id"],
                        source_chunk_id=source_chunk_id,
                    ),
                    "text": text,
                }
            )

    for handoff_row in handoff_display_rows[:top_k]:
        citations.append(
            {
                "paper_id": handoff_row["paper_id"],
                "source_chunk_id": handoff_row["source_chunk_id"],
                "source_id": handoff_row["handoff_id"],
                "page_num": handoff_row["page_num"],
                "section_path": handoff_row["section_path"],
                "title": handoff_row["title"],
                "anchor_text": handoff_row["anchor_text"],
                "text_preview": handoff_row["text_preview"],
                "content_type": handoff_row["content_type"],
                "score": handoff_row["score"],
                "citation_jump_url": handoff_row["citation_jump_url"],
            }
        )
        evidence_blocks.append(
            {
                "evidence_id": handoff_row["handoff_id"],
                "source_type": "paper",
                "source_chunk_id": handoff_row["source_chunk_id"],
                "paper_id": handoff_row["paper_id"],
                "page_num": handoff_row["page_num"],
                "section_path": handoff_row["section_path"],
                "content_type": handoff_row["content_type"],
                "text": handoff_row["text"],
                "score": handoff_row["score"],
                "rerank_score": handoff_row["score"],
                "support_status": "supported",
                "citation_jump_url": handoff_row["citation_jump_url"],
            }
        )

    for cand in display_candidates:
        if any(existing["source_chunk_id"] == cand.source_chunk_id for existing in citations):
            continue
        source_payload = get_evidence_source_payload(cand.source_chunk_id) or {}
        citation_jump_url = source_payload.get("citation_jump_url") or build_citation_jump_url(
            paper_id=cand.paper_id,
            source_chunk_id=cand.source_chunk_id,
        )
        page_num = source_payload.get("page_num")
        is_summary_display = is_summary_candidate(cand) or (source_payload.get("section_path") == "_paper")
        section_path = "summary" if is_summary_display else (source_payload.get("section_path") or cand.section_id)
        support_status = next(
            (
                claim.support_status
                for claim in contract.claims
                if cand.source_chunk_id in claim.supporting_source_chunk_ids
            ),
            None,
        )
        summary_record = summary_record_map.get(cand.paper_id) if is_summary_display else None
        raw_text = (
            build_summary_display_text(summary_record)
            if summary_record
            else (source_payload.get("content") or cand.anchor_text)
        )
        text = clean_display_evidence_text(str(raw_text or ""), title=paper_title_map.get(cand.paper_id))
        if not text:
            continue
        citation = {
            "paper_id": cand.paper_id,
            "source_chunk_id": cand.source_chunk_id,
            "page_num": page_num,
            "section_path": section_path,
            "title": paper_title_map.get(cand.paper_id) or cand.paper_id,
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

    if is_compare_family(routing.query_family):
        cited_paper_ids = {citation["paper_id"] for citation in citations}
        for paper_id in paper_scope or []:
            if paper_id in cited_paper_ids:
                continue
            summary_record = summary_record_map.get(paper_id)
            if not summary_record:
                continue
            representative_ids = list(summary_record.get("representative_source_chunk_ids") or [])
            representative_id = str(representative_ids[0] or "").strip() if representative_ids else ""
            if not representative_id:
                continue
            text = build_summary_display_text(summary_record)
            if not text:
                continue
            citation_jump_url = build_citation_jump_url(
                paper_id=paper_id,
                source_chunk_id=representative_id,
            )
            citation = {
                "paper_id": paper_id,
                "source_chunk_id": representative_id,
                "page_num": 1,
                "section_path": "summary",
                "title": paper_title_map.get(paper_id) or paper_id,
                "anchor_text": text,
                "text_preview": text[:300],
                "content_type": "text",
                "score": 0.0,
                "citation_jump_url": citation_jump_url,
            }
            citations.append(citation)
            evidence_blocks.append(
                {
                    "evidence_id": representative_id,
                    "source_type": "paper",
                    "source_chunk_id": representative_id,
                    "paper_id": paper_id,
                    "page_num": 1,
                    "section_path": "summary",
                    "content_type": "text",
                    "text": text,
                    "score": 0.0,
                    "rerank_score": 0.0,
                    "support_status": None,
                    "citation_jump_url": citation_jump_url,
                }
            )

    append_abstain_scope_fallback(
        citations=citations,
        evidence_blocks=evidence_blocks,
        paper_scope=paper_scope,
        paper_title_map=paper_title_map,
    )

    answer_text = await generate_answer_from_citations(
        query=normalized_query,
        citations=citations[:top_k],
        paper_summaries=summary_records[: max(1, len(paper_scope or []))] if include_summary_records else None,
        query_family=routing.query_family,
    )
    typed_blocks = [EvidenceBlock.model_validate(block) for block in evidence_blocks]
    truthfulness_report = get_truthfulness_service().evaluate_text(
        text=answer_text,
        evidence_blocks=typed_blocks,
    )
    truthfulness_mode = truthfulness_report.get("answerMode") or contract.answer_mode
    answer_mode = truthfulness_mode
    if answer_mode == "abstain" and citations and not re.search(r"(insufficient evidence|证据不足|无法基于所提供的证据|cannot answer confidently)", answer_text, re.IGNORECASE):
        answer_mode = "partial"
    claims = get_truthfulness_service().report_to_answer_claims(truthfulness_report)
    truthfulness_summary = {
        **truthfulness_report.get("summary", {}),
        "citation_coverage": quality.citation_support_score,
    }
    runtime_truth = pack.diagnostics.get("runtime_truth", {})
    recovery_actions = build_recovery_actions(
        scope="rag",
        answer_mode=answer_mode,
        task_family=routing.task_family,
        execution_mode=resolved_execution_mode,
        truthfulness_report=truthfulness_report,
        degraded_conditions=runtime_truth.get("degraded_conditions", []) + execution_mode_degraded_conditions,
        recovery_entry={
            "task_family": routing.task_family,
            "entry_type": "read",
            "paper_ids": list(paper_scope or []),
        },
    )

    fallback_used = bool(
        pack.diagnostics.get("dense_fallback_used", 0.0) > 0
        or runtime_truth.get("fallback_events")
    )
    phase6_runtime = build_phase6_runtime_contract(
        answer_mode=answer_mode,
        degraded_conditions=runtime_truth.get("degraded_conditions", []) + execution_mode_degraded_conditions,
        recovery_actions=recovery_actions,
        truthfulness_report=truthfulness_report,
        truthfulness_summary=truthfulness_summary,
        retrieval_evaluator=pack.diagnostics.get("retrieval_evaluator"),
        retrieval_diagnostics=pack.diagnostics,
        iterative_actions=pack.diagnostics.get("iterative_actions"),
        fallback_used=fallback_used,
        fallback_events=runtime_truth.get("fallback_events", []),
        recovery_entry={
            "task_family": routing.task_family,
            "entry_type": "read",
            "paper_ids": list(paper_scope or []),
        },
    )
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
        "degraded_conditions": runtime_truth.get("degraded_conditions", []) + execution_mode_degraded_conditions,
        "phase6_runtime": phase6_runtime,
        "cost_estimate": round(candidate_count * 0.00002, 6),
        "answer_mode": answer_mode,
        "error_state": error_state,
        "task_family": routing.task_family,
        "execution_mode": resolved_execution_mode,
        "truthfulness_required": routing.truthfulness_required,
        "truthfulness_report_summary": truthfulness_summary,
        "query_normalized": normalized_query != query,
        "normalized_query": normalized_query,
        "retrieval_plane_policy": {
            **routing.retrieval_plane_policy,
            "requested_execution_mode": routing.execution_mode,
            "mode": resolved_execution_mode,
        },
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
            "phase6_runtime": phase6_runtime,
        },
        "trace": trace_payload,
        "trace_id": trace,
        "run_id": run,
        "retrieval_trace_id": trace,
        "runtime_truth": runtime_truth,
        "cost_estimate": trace_payload["cost_estimate"],
        "error_state": error_state,
        "task_family": routing.task_family,
        "execution_mode": resolved_execution_mode,
        "truthfulness_required": routing.truthfulness_required,
        "truthfulness_summary": truthfulness_summary,
        "truthfulness_report": truthfulness_report,
        "retrieval_plane_policy": trace_payload["retrieval_plane_policy"],
        "degraded_conditions": trace_payload["degraded_conditions"],
        "recovery_actions": recovery_actions,
        "phase6_runtime": phase6_runtime,
    }


def build_answer_contract_payload_sync(
    **kwargs: Any,
) -> dict[str, Any]:
    """Compatibility wrapper for sync callers outside the request path."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(build_answer_contract_payload(**kwargs))
    raise RuntimeError("build_answer_contract_payload_sync cannot run inside an active event loop")
