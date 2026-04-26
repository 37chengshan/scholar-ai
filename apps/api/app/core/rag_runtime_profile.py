"""Single-source runtime contract for ScholarAI official RAG chain.

This module defines the only supported official runtime profile and provides
validation helpers used by config/startup/benchmark guards.
"""

from __future__ import annotations

from typing import Any


OFFICIAL_RUNTIME_PROFILE = "api_flash_qwen_rerank_glm"
OFFICIAL_EMBEDDING_PROVIDER = "tongyi"
OFFICIAL_EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"
OFFICIAL_RERANKER_PROVIDER = "qwen_api"
OFFICIAL_RERANKER_MODEL = "qwen3-vl-rerank"
OFFICIAL_LLM_PROVIDER = "zhipu"
OFFICIAL_LLM_MODEL = "glm-4.5-air"
OFFICIAL_RETRIEVAL_BRANCH = "api_flash_dense"

OFFICIAL_ACTIVE_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}

DISABLED_RETRIEVAL_BRANCHES = (
    "qwen_dense",
    "bge_dense",
    "specter2_scientific",
    "academic_hybrid",
    "graph_branch",
    "sparse_branch",
)

DEPRECATED_BRANCH_TOKENS = (
    "bge",
    "specter2",
    "academic_hybrid",
    "qwen_dual",
    "bge_dual",
)


class RagRuntimeValidationError(RuntimeError):
    """Raised when active runtime diverges from official contract."""


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_deprecated_token(value: Any) -> bool:
    normalized = _normalize(value)
    if not normalized:
        return False
    return any(token in normalized for token in DEPRECATED_BRANCH_TOKENS)


def validate_runtime_contract(
    *,
    runtime_profile: str,
    embedding_provider: str,
    embedding_model: str,
    reranker_provider: str,
    reranker_model: str,
    llm_provider: str,
    llm_model: str,
    additional_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate active runtime against official contract.

    Raises:
        RagRuntimeValidationError: when any contract rule is violated.
    """
    blocked_reasons: list[str] = []

    if _normalize(runtime_profile) != OFFICIAL_RUNTIME_PROFILE:
        blocked_reasons.append(
            f"RAG_RUNTIME_PROFILE must be {OFFICIAL_RUNTIME_PROFILE}, got {runtime_profile!r}"
        )

    if _normalize(embedding_provider) != OFFICIAL_EMBEDDING_PROVIDER:
        blocked_reasons.append(
            f"EMBEDDING_PROVIDER must be {OFFICIAL_EMBEDDING_PROVIDER}, got {embedding_provider!r}"
        )
    if _normalize(embedding_model) != OFFICIAL_EMBEDDING_MODEL:
        blocked_reasons.append(
            f"EMBEDDING_MODEL must be {OFFICIAL_EMBEDDING_MODEL}, got {embedding_model!r}"
        )

    if _normalize(reranker_provider) != OFFICIAL_RERANKER_PROVIDER:
        blocked_reasons.append(
            f"RERANKER_PROVIDER must be {OFFICIAL_RERANKER_PROVIDER}, got {reranker_provider!r}"
        )
    if _normalize(reranker_model) != OFFICIAL_RERANKER_MODEL:
        blocked_reasons.append(
            f"RERANKER_MODEL must be {OFFICIAL_RERANKER_MODEL}, got {reranker_model!r}"
        )

    if _normalize(llm_provider) != OFFICIAL_LLM_PROVIDER:
        blocked_reasons.append(f"LLM_PROVIDER must be {OFFICIAL_LLM_PROVIDER}, got {llm_provider!r}")
    if _normalize(llm_model) != OFFICIAL_LLM_MODEL:
        blocked_reasons.append(f"LLM_MODEL must be {OFFICIAL_LLM_MODEL}, got {llm_model!r}")

    deprecated_hits: list[str] = []
    for key, value in (additional_values or {}).items():
        if _contains_deprecated_token(value):
            deprecated_hits.append(f"{key}={value}")

    if deprecated_hits:
        blocked_reasons.append(
            "Deprecated runtime branch detected: " + ", ".join(sorted(deprecated_hits))
        )

    if blocked_reasons:
        raise RagRuntimeValidationError("; ".join(blocked_reasons))

    return {
        "runtime_profile": OFFICIAL_RUNTIME_PROFILE,
        "embedding_provider": OFFICIAL_EMBEDDING_PROVIDER,
        "embedding_model": OFFICIAL_EMBEDDING_MODEL,
        "reranker_provider": OFFICIAL_RERANKER_PROVIDER,
        "reranker_model": OFFICIAL_RERANKER_MODEL,
        "llm_provider": OFFICIAL_LLM_PROVIDER,
        "llm_model": OFFICIAL_LLM_MODEL,
        "deprecated_branch_used": False,
        "status": "PASS",
    }
