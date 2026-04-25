"""Retrieval branch registry for the active API-first RAG runtime.

Only the api_flash_dense branch is allowed in the official runtime. Historical
branches are listed as deprecated for audit/reporting but must not be activated
by production code or official benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.core.rag_runtime_profile import (
    ACTIVE_RAG_RUNTIME_PROFILE,
    ACTIVE_COLLECTIONS,
    assert_no_deprecated_runtime_tokens,
)


@dataclass(frozen=True)
class RetrievalBranch:
    name: str
    enabled: bool
    provider: str
    model: str
    collections: Mapping[str, str]
    vector_field: str = "embedding"


ACTIVE_RETRIEVAL_BRANCH = RetrievalBranch(
    name="api_flash_dense",
    enabled=True,
    provider="tongyi",
    model="tongyi-embedding-vision-flash-2026-03-06",
    collections=ACTIVE_COLLECTIONS,
)

DEPRECATED_RETRIEVAL_BRANCHES = {
    "qwen_dense": "Deprecated local Qwen embedding branch",
    "bge_dense": "Deprecated BGE-M3 embedding branch",
    "specter2_scientific": "Deprecated SPECTER2 experimental branch",
    "academic_hybrid": "Deprecated multi-branch hybrid runtime",
    "graph_branch": "Graph retrieval is disabled for the single-chain runtime",
    "sparse_branch": "Sparse branch is not active in this runtime profile",
}


def get_active_retrieval_branch() -> RetrievalBranch:
    return ACTIVE_RETRIEVAL_BRANCH


def get_active_collections() -> Mapping[str, str]:
    return ACTIVE_RETRIEVAL_BRANCH.collections


def validate_retrieval_runtime(branch_names: list[str] | tuple[str, ...]) -> None:
    """Fail when deprecated retrieval branches are requested."""
    assert_no_deprecated_runtime_tokens(branch_names)
    for branch in branch_names:
        if branch != ACTIVE_RETRIEVAL_BRANCH.name:
            raise ValueError(
                f"Retrieval branch '{branch}' is not allowed in "
                f"{ACTIVE_RAG_RUNTIME_PROFILE}; expected {ACTIVE_RETRIEVAL_BRANCH.name}."
            )


def retrieval_registry_report() -> dict[str, object]:
    return {
        "runtime_profile": ACTIVE_RAG_RUNTIME_PROFILE,
        "active_branch": ACTIVE_RETRIEVAL_BRANCH.name,
        "active_provider": ACTIVE_RETRIEVAL_BRANCH.provider,
        "active_model": ACTIVE_RETRIEVAL_BRANCH.model,
        "active_collections": dict(ACTIVE_RETRIEVAL_BRANCH.collections),
        "deprecated_branches": dict(DEPRECATED_RETRIEVAL_BRANCHES),
    }
