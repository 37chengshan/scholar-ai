"""Retrieval branch registry constrained to official api_flash runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from app.core.rag_runtime_profile import (
    OFFICIAL_ACTIVE_COLLECTIONS,
    OFFICIAL_EMBEDDING_MODEL,
    OFFICIAL_RETRIEVAL_BRANCH,
)


BranchName = Literal["api_flash_dense", "bm25"]
StageName = Literal["raw", "rule", "llm"]


class RetrievalPreflightError(RuntimeError):
    """Raised when retrieval preflight or branch safety checks fail."""


@dataclass(frozen=True)
class DenseBranchConfig:
    branch: BranchName
    embedding_model: str
    expected_dim: int
    vector_field: str
    raw_collection: str
    rule_collection: str
    llm_collection: str
    enabled: bool

    def collection_for_stage(self, stage: StageName) -> str:
        if stage == "raw":
            return self.raw_collection
        if stage == "rule":
            return self.rule_collection
        return self.llm_collection


API_FLASH_BRANCH = DenseBranchConfig(
    branch="api_flash_dense",
    embedding_model=OFFICIAL_EMBEDDING_MODEL,
    expected_dim=1024,
    vector_field="embedding",
    raw_collection=OFFICIAL_ACTIVE_COLLECTIONS["raw"],
    rule_collection=OFFICIAL_ACTIVE_COLLECTIONS["rule"],
    llm_collection=OFFICIAL_ACTIVE_COLLECTIONS["llm"],
    enabled=True,
)


def _stage_collection_map() -> dict[StageName, str]:
    return {
        "raw": API_FLASH_BRANCH.raw_collection,
        "rule": API_FLASH_BRANCH.rule_collection,
        "llm": API_FLASH_BRANCH.llm_collection,
    }


def infer_stage_from_collection(collection_name: str) -> Optional[StageName]:
    for stage, name in _stage_collection_map().items():
        if collection_name == name:
            return stage
    return None


def get_qwen_collection(stage: StageName) -> str:
    """Compatibility shim for legacy call sites.

    Despite historical naming, this now returns api_flash collections only.
    """
    return _stage_collection_map()[stage]


def get_dense_branch_config(branch: BranchName) -> DenseBranchConfig:
    if branch == "api_flash_dense":
        return API_FLASH_BRANCH
    raise RetrievalPreflightError(f"Branch '{branch}' is not a dense branch")


def is_branch_enabled(branch: str) -> bool:
    if branch == "bm25":
        return True
    if branch == OFFICIAL_RETRIEVAL_BRANCH:
        return True
    return False


def _is_deprecated_branch(branch: str) -> bool:
    normalized = (branch or "").strip().lower()
    return normalized in {
        "qwen",
        "qwen_dense",
        "specter2",
        "specter2_scientific",
        "bge_dense",
        "bge_dual",
        "qwen_dual",
        "academic_hybrid",
        "graph_branch",
        "sparse_branch",
    }


def ensure_branch_collection_allowed(branch: str, collection_name: str) -> None:
    normalized_branch = (branch or "").strip().lower() or OFFICIAL_RETRIEVAL_BRANCH

    if _is_deprecated_branch(normalized_branch):
        raise RetrievalPreflightError(
            "Deprecated retrieval branch is not allowed in "
            "api_flash_qwen_rerank_glm runtime."
        )

    if normalized_branch not in {OFFICIAL_RETRIEVAL_BRANCH, "bm25"}:
        raise RetrievalPreflightError(
            "Deprecated retrieval branch is not allowed in "
            "api_flash_qwen_rerank_glm runtime."
        )

    if normalized_branch == "bm25":
        return

    allowed = {
        API_FLASH_BRANCH.raw_collection,
        API_FLASH_BRANCH.rule_collection,
        API_FLASH_BRANCH.llm_collection,
    }
    if collection_name not in allowed:
        raise RetrievalPreflightError(
            "Illegal branch-to-collection mapping: "
            f"branch={normalized_branch}, collection={collection_name}, allowed={sorted(allowed)}"
        )


def assert_dim_match(
    *,
    branch: str,
    model: str,
    collection: str,
    vector_field: str,
    query_dim: int,
    collection_dim: int,
) -> None:
    if query_dim != collection_dim:
        raise RetrievalPreflightError(
            "Embedding dim mismatch: "
            f"branch={branch}, model={model}, collection={collection}, "
            f"vector_field={vector_field}, query_dim={query_dim}, collection_dim={collection_dim}"
        )


def qwen_branch_expected_dim() -> int:
    """Compatibility shim: returns active api_flash expected dimension."""
    return API_FLASH_BRANCH.expected_dim


def specter2_branch_expected_dim() -> int:
    raise RetrievalPreflightError(
        "Deprecated retrieval branch is not allowed in api_flash_qwen_rerank_glm runtime."
    )


def get_specter2_collection(stage: StageName) -> str:
    raise RetrievalPreflightError(
        "Deprecated retrieval branch is not allowed in api_flash_qwen_rerank_glm runtime."
    )


def resolve_active_qwen_collection() -> str:
    """Compatibility shim for legacy naming, now pinned to api_flash llm collection."""
    return API_FLASH_BRANCH.llm_collection
