from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.database import AsyncSessionLocal
from app.core.vector_store_repository import get_vector_store_repository
from app.models import Paper
from app.models.retrieval import SearchConstraints
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
from app.rag_v3.schemas import EvidenceBlock, EvidenceCandidate, EvidencePack
from app.services.paper_display_metadata import sanitize_paper_display_metadata
from app.utils.zhipu_client import ZhipuLLMClient
from app.services.evidence_contract_service import (
    ARTIFACTS_ROOT,
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.services.phase_i_routing_service import get_phase_i_routing_service
from app.services.truthfulness_service import get_truthfulness_service
from sqlalchemy import select
from sqlalchemy.orm import selectinload

ARTIFACT_ROOT = ARTIFACTS_ROOT / "papers"
RUNTIME_PROFILE = get_active_rag_runtime_profile()
_QUERY_PREFIX_PATTERN = re.compile(r"^\s*(再次回答|继续分析|继续回答|继续|重新回答|重新分析|再回答一遍|重新来过)\s*[:：,，-]?\s*", re.IGNORECASE)
_CONTRIBUTION_QUERY_PATTERN = re.compile(
    r"(核心贡献|主要贡献|贡献点|创新点|创新|主要解决.*问题|解决.*问题|研究问题|研究动机|motivation|contribution|problem)",
    re.IGNORECASE,
)
_SUMMARY_SECTION_HINTS = ("abstract", "introduction", "motivation", "contribution", "summary", "overview")
_SUMMARY_SECTION_IDS = {"_paper", "paper_summary", "summary"}
_LOW_SIGNAL_COMPARE_PATTERNS = (
    re.compile(r"let'?s think step[- ]by[- ]step", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"GLYPH<\d+>", re.IGNORECASE),
)
_SUMMARY_PREFIX_RE = re.compile(r"^\[Paper Summary:[^\]]+\]\s*", re.IGNORECASE)
_BRACKET_METADATA_LINE_RE = re.compile(r"^\[[^\]]+\]\s*$", re.IGNORECASE)


def _safe_stage(stage: str) -> str:
    return stage if stage in RUNTIME_PROFILE.collections else "rule"


def _normalize_query_text(query: str) -> str:
    normalized = (query or "").strip()
    while True:
        cleaned = _QUERY_PREFIX_PATTERN.sub("", normalized)
        if cleaned == normalized:
            break
        normalized = cleaned.strip()
    return normalized


def _is_summary_seeking_query(query: str) -> bool:
    return bool(_CONTRIBUTION_QUERY_PATTERN.search(query or ""))


def _is_compare_family(query_family: str | None) -> bool:
    return query_family in {"compare", "cross_paper", "survey", "related_work", "method_evolution", "conflicting_evidence"}


def _is_summary_candidate(candidate: EvidenceCandidate) -> bool:
    section_id = (candidate.section_id or "").strip().lower()
    if section_id in _SUMMARY_SECTION_IDS:
        return True
    return "summary_index" in candidate.candidate_sources


def _is_low_signal_compare_candidate(candidate: EvidenceCandidate) -> bool:
    text = (candidate.anchor_text or "").strip()
    if not text:
        return True
    return any(pattern.search(text) for pattern in _LOW_SIGNAL_COMPARE_PATTERNS)


def _clean_display_evidence_text(text: str, *, title: str | None = None) -> str:
    cleaned = str(text or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return ""

    cleaned = _SUMMARY_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"GLYPH<\d+>", " ", cleaned)

    lines: list[str] = []
    normalized_title = (title or "").strip()
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _BRACKET_METADATA_LINE_RE.match(line):
            continue
        if normalized_title and line == normalized_title:
            continue
        lines.append(line)

    collapsed = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return collapsed


def _select_display_candidates(
    candidates: list[EvidenceCandidate],
    *,
    top_k: int,
    query_family: str | None,
) -> list[EvidenceCandidate]:
    if not candidates:
        return []

    if not _is_compare_family(query_family):
        return candidates[:top_k]

    high_signal = [
        candidate
        for candidate in candidates
        if not _is_summary_candidate(candidate) and not _is_low_signal_compare_candidate(candidate)
    ]
    if high_signal:
        return high_signal[:top_k]

    without_summary = [candidate for candidate in candidates if not _is_summary_candidate(candidate)]
    if without_summary:
        return without_summary[:top_k]

    without_low_signal = [candidate for candidate in candidates if not _is_low_signal_compare_candidate(candidate)]
    if without_low_signal:
        return without_low_signal[:top_k]

    return candidates[:top_k]


def _normalize_handoff_evidence_rows(handoff_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in handoff_evidence or []:
        if not isinstance(row, dict):
            continue
        paper_id = str(row.get("paper_id") or row.get("paperId") or "").strip()
        source_chunk_id = str(row.get("source_chunk_id") or row.get("sourceChunkId") or "").strip()
        text = str(row.get("text") or "").strip()
        if not paper_id or not source_chunk_id:
            continue
        normalized_rows.append(
            {
                "handoff_id": str(row.get("handoff_id") or row.get("handoffId") or "").strip(),
                "paper_id": paper_id,
                "source_chunk_id": source_chunk_id,
                "page_num": row.get("page_num", row.get("pageNum")),
                "claim": str(row.get("claim") or "").strip(),
                "dimension_id": str(row.get("dimension_id") or row.get("dimensionId") or "").strip(),
                "section_path": str(row.get("section_path") or row.get("sectionPath") or "").strip(),
                "content_type": str(row.get("content_type") or row.get("contentType") or "text").strip() or "text",
                "text": text,
                "citation_jump_url": str(row.get("citation_jump_url") or row.get("citationJumpUrl") or "").strip(),
                "title": str(row.get("title") or "").strip(),
            }
        )
    return normalized_rows


async def _load_paper_display_title_map(user_id: str, paper_ids: list[str] | None) -> dict[str, str]:
    scoped_paper_ids = [paper_id for paper_id in dict.fromkeys(paper_ids or []) if paper_id]
    if not scoped_paper_ids:
        return {}

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Paper)
                .options(selectinload(Paper.upload_history))
                .where(
                    Paper.user_id == user_id,
                    Paper.id.in_(scoped_paper_ids),
                )
            )
            papers = result.scalars().all()
    except Exception:
        return {}

    display_titles: dict[str, str] = {}
    for paper in papers:
        latest_upload_filename = None
        if getattr(paper, "upload_history", None):
            latest_row = max(
                paper.upload_history,
                key=lambda row: row.created_at or getattr(paper, "updated_at", None) or getattr(paper, "created_at", None),
            )
            latest_upload_filename = latest_row.filename
        display = sanitize_paper_display_metadata(
            paper_id=paper.id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            venue=paper.venue,
            fallback_title=latest_upload_filename,
        )
        display_titles[paper.id] = display["title"] or paper.id
    return display_titles


def _build_summary_record_map(summary_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("paper_id") or ""): record
        for record in summary_records
        if str(record.get("paper_id") or "").strip()
    }


def _append_abstain_scope_fallback(
    *,
    citations: list[dict[str, Any]],
    evidence_blocks: list[dict[str, Any]],
    paper_scope: list[str] | None,
    paper_title_map: dict[str, str],
) -> None:
    if citations or evidence_blocks or not paper_scope:
        return

    fallback_paper_id = str(paper_scope[0] or "").strip()
    if not fallback_paper_id:
        return

    fallback_chunk_id = f"paper-scope-fallback::{fallback_paper_id}"
    fallback_title = paper_title_map.get(fallback_paper_id) or fallback_paper_id
    fallback_jump_url = build_citation_jump_url(
        paper_id=fallback_paper_id,
        source_chunk_id=fallback_chunk_id,
    )
    fallback_anchor = "当前回答未达到可直接作答的证据阈值，请回到原文继续核验。"

    citations.append(
        {
            "paper_id": fallback_paper_id,
            "source_chunk_id": fallback_chunk_id,
            "source_id": fallback_chunk_id,
            "page_num": 1,
            "section_path": "paper_scope_fallback",
            "title": fallback_title,
            "anchor_text": fallback_anchor,
            "text_preview": fallback_anchor,
            "content_type": "text",
            "score": 0.0,
            "citation_jump_url": fallback_jump_url,
        }
    )
    evidence_blocks.append(
        {
            "evidence_id": fallback_chunk_id,
            "source_type": "paper",
            "source_chunk_id": fallback_chunk_id,
            "paper_id": fallback_paper_id,
            "page_num": 1,
            "section_path": "paper_scope_fallback",
            "content_type": "text",
            "text": fallback_anchor,
            "score": 0.0,
            "rerank_score": 0.0,
            "support_status": "unsupported",
            "citation_jump_url": fallback_jump_url,
        }
    )


def _build_summary_display_text(summary_record: dict[str, Any]) -> str:
    text = (
        summary_record.get("paper_summary")
        or summary_record.get("abstract")
        or summary_record.get("method_summary")
        or summary_record.get("result_summary")
        or ""
    )
    return _clean_display_evidence_text(str(text or ""), title=str(summary_record.get("title") or ""))


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


def _resolve_runtime_execution_mode(
    *,
    requested_execution_mode: str,
    paper_scope: list[str] | None,
) -> tuple[str, list[str]]:
    degraded_conditions: list[str] = []
    if requested_execution_mode != "global_review":
        return requested_execution_mode, degraded_conditions

    # The current main-path service remains a local evidence answer path.
    degraded_conditions.append("global_review_fallback_to_local_evidence")
    return "local_evidence", degraded_conditions


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
        output_fields=[
            "source_chunk_id",
            "paper_id",
            "content_type",
            "section",
            "page_num",
            "content_data",
        ],
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
        paper_scope=paper_scope,
        retrieval_depth=retrieval_depth,
        section_paths=section_paths,
        page_from=page_from,
        page_to=page_to,
        content_types=content_types,
    )

    if paper_scope and _is_summary_seeking_query(query):
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


def _build_answer_generation_prompt(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    summary_lines: list[str] = []
    for index, summary in enumerate(paper_summaries or [], start=1):
        summary_lines.append(
            "\n".join(
                [
                    f"[Paper Summary {index}]",
                    f"paper_id: {summary.get('paper_id') or ''}",
                    f"title: {summary.get('title') or ''}",
                    f"abstract: {summary.get('abstract') or ''}",
                    f"paper_summary: {summary.get('paper_summary') or ''}",
                    f"method_summary: {summary.get('method_summary') or ''}",
                    f"result_summary: {summary.get('result_summary') or ''}",
                ]
            )
        )

    evidence_lines: list[str] = []
    for index, citation in enumerate(citations, start=1):
        section_path = citation.get("section_path") or "unknown"
        page_num = citation.get("page_num")
        score = citation.get("score")
        evidence_lines.append(
            "\n".join(
                [
                    f"[Evidence {index}]",
                    f"paper_id: {citation.get('paper_id') or ''}",
                    f"section: {section_path}",
                    f"page: {page_num if page_num is not None else 'unknown'}",
                    f"score: {score if score is not None else 'unknown'}",
                    f"text: {citation.get('text_preview') or citation.get('anchor_text') or ''}",
                ]
            )
        )

    system_prompt = (
        "你是 ScholarAI 的论文问答回答器。"
        "你必须只基于提供的证据回答，不要编造。"
        "优先输出简洁、结构化、直接回答用户问题的中文。"
        "如果证据不足，明确说明证据不足以及缺的是什么。"
        "如果问题是在问论文的贡献、创新、研究问题或动机，优先综合摘要、引言和贡献相关证据。"
    )
    user_prompt = (
        f"用户问题：{query}\n\n"
        "请基于以下证据回答。"
        "先直接回答问题，再给出 2-4 个要点；不要逐字复述原文；不要输出与问题无关的解释。\n\n"
        + ("\n\n".join(summary_lines) + "\n\n" if summary_lines else "")
        + "\n\n".join(evidence_lines)
    )
    return system_prompt, user_prompt


def _build_compare_answer_generation_prompt(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    summary_by_paper: dict[str, dict[str, Any]] = {
        str(item.get("paper_id") or ""): item
        for item in (paper_summaries or [])
        if str(item.get("paper_id") or "").strip()
    }

    evidence_by_paper: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        paper_id = str(citation.get("paper_id") or "").strip()
        if not paper_id:
            continue
        evidence_by_paper.setdefault(paper_id, []).append(citation)

    paper_blocks: list[str] = []
    for index, paper_id in enumerate(evidence_by_paper.keys(), start=1):
        summary = summary_by_paper.get(paper_id, {})
        paper_evidence = evidence_by_paper.get(paper_id, [])
        first_evidence = paper_evidence[0] if paper_evidence else {}
        title = str(summary.get("title") or first_evidence.get("title") or paper_id)
        evidence_lines: list[str] = []
        for evidence in paper_evidence[:4]:
            section_path = str(evidence.get("section_path") or "unknown")
            snippet = str(evidence.get("text_preview") or evidence.get("anchor_text") or "").strip()
            if not snippet:
                continue
            evidence_lines.append(f"- [{section_path}] {snippet}")
        paper_blocks.append(
            "\n".join(
                [
                    f"[Paper {index}]",
                    f"paper_id: {paper_id}",
                    f"title: {title}",
                    f"summary: {summary.get('paper_summary') or summary.get('abstract') or ''}",
                    "evidence:",
                    *evidence_lines,
                ]
            ).strip()
        )

    system_prompt = (
        "你是 ScholarAI 的跨论文比较回答器。"
        "你必须只根据提供的证据进行比较，不要补全不存在的共同点。"
        "输出中文，优先给出短而直接的比较结论。"
        "如果共同点证据弱，可以明确写“当前证据下共同点有限”，不要硬凑。"
        "如果只能回答局部差异，也要先给出已知差异，再说明证据缺口。"
        "下一步研究问题必须从已有证据推导，不要写空泛套话。"
    )
    user_prompt = (
        f"用户问题：{query}\n\n"
        "请基于以下按论文整理的证据进行比较回答。"
        "要求：\n"
        "1. 先给 1 句直接结论。\n"
        "2. 核心差异：优先列出证据最强的 2-3 条；每条都明确是哪篇论文的什么维度。\n"
        "3. 共同点：只写被两篇论文都支持的点；如果证据不够，明确写“当前证据下共同点有限”，并说明是哪些维度缺证据。\n"
        "4. 下一步研究问题：给 1-2 条，并明确是由哪篇论文的证据缺口或局限引出的。\n"
        "5. 不要为了凑结构写空话；如果只有差异有把握，就重点回答差异。\n\n"
        + "\n\n".join(paper_blocks)
    )
    return system_prompt, user_prompt


def _build_compare_answer_fallback(
    *,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> str:
    summary_by_paper: dict[str, dict[str, Any]] = {
        str(item.get("paper_id") or ""): item
        for item in (paper_summaries or [])
        if str(item.get("paper_id") or "").strip()
    }
    evidence_by_paper: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        paper_id = str(citation.get("paper_id") or "").strip()
        if not paper_id:
            continue
        evidence_by_paper.setdefault(paper_id, []).append(citation)

    if not evidence_by_paper:
        return "当前证据不足以形成可靠的跨论文比较。"

    paper_ids = list(evidence_by_paper.keys())
    paper_labels: dict[str, str] = {}
    for index, paper_id in enumerate(paper_ids, start=1):
        summary = summary_by_paper.get(paper_id, {})
        first_evidence = evidence_by_paper[paper_id][0] if evidence_by_paper[paper_id] else {}
        paper_labels[paper_id] = str(summary.get("title") or first_evidence.get("title") or f"论文{index}")

    difference_lines: list[str] = []
    known_sections: dict[str, set[str]] = {}
    for paper_id in paper_ids:
        label = paper_labels[paper_id]
        seen_sections: set[str] = set()
        known_sections[paper_id] = seen_sections
        for evidence in evidence_by_paper[paper_id]:
            section_path = str(evidence.get("section_path") or "unknown").strip() or "unknown"
            section_key = section_path.lower()
            if section_key in seen_sections:
                continue
            seen_sections.add(section_key)
            snippet = str(evidence.get("text_preview") or evidence.get("anchor_text") or "").strip()
            if not snippet:
                continue
            snippet = re.sub(r"\s+", " ", snippet)
            if len(snippet) > 120:
                snippet = f"{snippet[:117].rstrip()}..."
            difference_lines.append(f"- {label} 在 {section_path} 上的证据显示：{snippet}")
            if len(difference_lines) >= 4:
                break
        if len(difference_lines) >= 4:
            break

    common_sections = set.intersection(*(sections for sections in known_sections.values() if sections)) if all(known_sections.values()) else set()
    if common_sections:
        commonality_text = "共同点：当前证据显示两篇论文都覆盖了 " + "、".join(sorted(common_sections)[:3]) + " 等维度，但共同结论仍需要更直接的对应证据。"
    else:
        commonality_text = "共同点：当前证据下共同点有限，现有证据主要支持各自的方法、结果或局限，缺少一一对应的共同结论证据。"

    question_lines: list[str] = []
    for paper_id in paper_ids[:2]:
        label = paper_labels[paper_id]
        sections = sorted(known_sections.get(paper_id) or [])
        if "limitations" in sections:
            question_lines.append(f"- {label} 的 limitations 证据提示后续应继续验证其已知局限在其他任务或数据条件下是否仍成立。")
        elif "results" in sections:
            question_lines.append(f"- {label} 当前主要给出了 results 证据，后续需要补充其方法假设和失败案例，才能做更完整的横向比较。")
        elif "method" in sections or "methods" in sections:
            question_lines.append(f"- {label} 当前主要有方法层证据，后续需要补充与结果或局限直接对应的证据。")

    if not question_lines:
        question_lines.append("- 现有证据还需要补足同一维度上的成对证据，尤其是共同实验设置、局限和失败案例。")

    conclusion = "基于当前证据，可以先确认两篇论文在研究切入点或实现路径上存在差异，但共同点和完整优劣判断仍受证据覆盖限制。"
    parts = [
        conclusion,
        "",
        "核心差异：",
        *(difference_lines or ["- 当前证据主要是零散片段，只能确认比较证据尚不充分。"]),
        "",
        commonality_text,
        "",
        "下一步研究问题：",
        *question_lines[:2],
    ]
    return "\n".join(parts).strip()


async def _generate_answer_from_citations(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
    query_family: str | None = None,
) -> str:
    if not citations:
        return "Insufficient evidence to answer confidently."

    if _is_compare_family(query_family):
        system_prompt, user_prompt = _build_compare_answer_generation_prompt(
            query=query,
            citations=citations,
            paper_summaries=paper_summaries,
        )
    else:
        system_prompt, user_prompt = _build_answer_generation_prompt(
            query=query,
            citations=citations,
            paper_summaries=paper_summaries,
        )
    client = ZhipuLLMClient(model=RUNTIME_PROFILE.llm_model, max_tokens=900, temperature=0.2)
    content = await client.simple_completion(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.2,
    )
    answer_text = str(content or "").strip()
    if _is_compare_family(query_family):
        if not answer_text or re.search(
            r"(insufficient evidence|证据不足|无法基于所提供的证据|无法根据提供的证据|cannot answer confidently)",
            answer_text,
            re.IGNORECASE,
        ):
            return _build_compare_answer_fallback(
                citations=citations,
                paper_summaries=paper_summaries,
            )
    return answer_text or "Insufficient evidence to answer confidently."


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
    normalized_query = _normalize_query_text(query)
    trace = trace_id or str(uuid4())
    run = run_id or str(uuid4())
    settings = get_settings()
    routing = get_phase_i_routing_service().route(
        query=normalized_query,
        query_family=query_family,
        paper_scope=paper_scope,
    )
    resolved_execution_mode, execution_mode_degraded_conditions = _resolve_runtime_execution_mode(
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
    summary_query = _is_summary_seeking_query(normalized_query)
    paper_title_map = await _load_paper_display_title_map(user_id, paper_scope)
    normalized_handoff_evidence = _normalize_handoff_evidence_rows(handoff_evidence)
    boosted_candidates = list(pack.candidates)
    if summary_query:
        boosted_candidates.sort(
            key=lambda cand: (
                1 if any(hint in (cand.section_id or "").lower() for hint in _SUMMARY_SECTION_HINTS) else 0,
                cand.rerank_score,
            ),
            reverse=True,
        )

    summary_records: list[dict[str, Any]] = []
    include_summary_records = bool(paper_scope) and (summary_query or _is_compare_family(routing.query_family))
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

    display_candidates = _select_display_candidates(
        boosted_candidates,
        top_k=top_k,
        query_family=routing.query_family,
    )
    summary_record_map = _build_summary_record_map(summary_records)

    handoff_display_rows: list[dict[str, Any]] = []
    if _is_compare_family(routing.query_family) and normalized_handoff_evidence:
        seen_handoff_ids: set[str] = set()
        for row in normalized_handoff_evidence:
            source_chunk_id = row["source_chunk_id"]
            handoff_id = str(row.get("handoff_id") or "").strip() or (
                f'{row["paper_id"]}::{source_chunk_id}::{row.get("dimension_id") or ""}::{row.get("claim") or ""}'
            )
            if handoff_id in seen_handoff_ids:
                continue
            seen_handoff_ids.add(handoff_id)
            text = _clean_display_evidence_text(
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
        is_summary_display = _is_summary_candidate(cand) or (source_payload.get("section_path") == "_paper")
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
            _build_summary_display_text(summary_record)
            if summary_record
            else (source_payload.get("content") or cand.anchor_text)
        )
        text = _clean_display_evidence_text(str(raw_text or ""), title=paper_title_map.get(cand.paper_id))
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

    if _is_compare_family(routing.query_family):
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
            text = _build_summary_display_text(summary_record)
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

    _append_abstain_scope_fallback(
        citations=citations,
        evidence_blocks=evidence_blocks,
        paper_scope=paper_scope,
        paper_title_map=paper_title_map,
    )

    answer_text = await _generate_answer_from_citations(
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
        "degraded_conditions": runtime_truth.get("degraded_conditions", []) + execution_mode_degraded_conditions,
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
