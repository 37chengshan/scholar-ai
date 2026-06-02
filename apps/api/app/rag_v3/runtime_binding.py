"""Runtime binding and retriever initialization for RAG pipeline.

Extracted from main_path_service.py to keep the orchestration layer under 800 lines.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.core.rag_runtime_profile import (
    get_active_rag_runtime_profile,
    get_collection_for_stage,
    get_embedding_model_for_policy,
)
from app.core.runtime_contract import build_online_binding, build_vector_store_binding
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.rerank.qwen3vl_rerank_adapter import get_rerank_runtime_binding
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from app.services.evidence_contract_service import ARTIFACTS_ROOT

ARTIFACT_ROOT = ARTIFACTS_ROOT / "papers"
RUNTIME_PROFILE = get_active_rag_runtime_profile()


def safe_stage(stage: str) -> str:
    return stage if stage in RUNTIME_PROFILE.collections else "rule"


def provider_runtime_truth(provider: Any, *, requested_mode: str, model: str) -> dict[str, Any]:
    if hasattr(provider, "get_runtime_binding"):
        return provider.get_runtime_binding().to_dict()
    return build_online_binding(
        component="embedding",
        provider_name=RUNTIME_PROFILE.embedding_provider,
        model=model,
        dimension=getattr(provider, "dim", None),
        supports_multimodal=False,
        requested_mode=requested_mode,
    ).to_dict()


def merge_runtime_modes(modes: list[str]) -> str:
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


def collect_runtime_events(bindings: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
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


def resolve_runtime_execution_mode(
    *,
    requested_execution_mode: str,
    paper_scope: list[str] | None,
) -> tuple[str, list[str]]:
    degraded_conditions: list[str] = []
    if requested_execution_mode != "global_review":
        return requested_execution_mode, degraded_conditions

    degraded_conditions.append("global_review_fallback_to_local_evidence")
    return "local_evidence", degraded_conditions


@lru_cache(maxsize=3)
def get_retriever(stage: str, embedding_model: str) -> HierarchicalRetriever:
    from pymilvus import connections

    stage = safe_stage(stage)
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
