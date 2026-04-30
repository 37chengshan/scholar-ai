"""RAG runtime profile contract for the online-first ScholarAI chain.

This module intentionally avoids importing provider SDKs or local model runtimes.
It is a lightweight guard used by config, benchmark scripts, and runtime traces to
prevent deprecated branches from silently re-entering the default RAG path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


ACTIVE_RAG_RUNTIME_PROFILE = "dashscope_qwen_online__qwen_rerank__glm_air"

ACTIVE_EMBEDDING_PROVIDER = "dashscope_qwen"
ACTIVE_EMBEDDING_MODEL_FLASH = "qwen_flash"
ACTIVE_EMBEDDING_MODEL_PRO = "qwen_pro"
ACTIVE_EMBEDDING_DIMENSION = 1024

ACTIVE_RERANKER_PROVIDER = "dashscope_qwen"
ACTIVE_RERANKER_MODEL = "qwen_rerank"

ACTIVE_LLM_PROVIDER = "zhipu"
ACTIVE_LLM_MODEL = "glm-4.5-air"

ACTIVE_VECTOR_STORE_BACKEND = "milvus"
ACTIVE_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}

PRO_QUERY_FAMILIES = {
    "numeric",
    "compare",
    "cross_paper",
    "survey",
    "related_work",
    "conflicting_evidence",
    "hard",
}

DEPRECATED_RUNTIME_TOKENS = {
    "bge",
    "bge-m3",
    "bge_reranker",
    "bge-reranker",
    "bge_dual",
    "specter2",
    "scientific_text",
    "qwen_dual",
    "academic_hybrid",
    "local_qwen_embedding",
    "local_qwen_reranker",
    "graph_branch",
}


@dataclass(frozen=True)
class RagRuntimeProfile:
    """Concrete active RAG profile.

    The profile is explicit about retrieval and generation planes so runtime
    traces can be honest even when the current repository still uses shim/local
    compatibility adapters under the hood.
    """

    name: str
    embedding_provider: str
    embedding_model_flash: str
    embedding_model_pro: str
    embedding_dimension: int
    reranker_provider: str
    reranker_model: str
    llm_provider: str
    llm_model: str
    vector_store_backend: str
    collections: Mapping[str, str]


ACTIVE_PROFILE = RagRuntimeProfile(
    name=ACTIVE_RAG_RUNTIME_PROFILE,
    embedding_provider=ACTIVE_EMBEDDING_PROVIDER,
    embedding_model_flash=ACTIVE_EMBEDDING_MODEL_FLASH,
    embedding_model_pro=ACTIVE_EMBEDDING_MODEL_PRO,
    embedding_dimension=ACTIVE_EMBEDDING_DIMENSION,
    reranker_provider=ACTIVE_RERANKER_PROVIDER,
    reranker_model=ACTIVE_RERANKER_MODEL,
    llm_provider=ACTIVE_LLM_PROVIDER,
    llm_model=ACTIVE_LLM_MODEL,
    vector_store_backend=ACTIVE_VECTOR_STORE_BACKEND,
    collections=ACTIVE_COLLECTIONS,
)


def normalize_runtime_token(value: object) -> str:
    """Normalize config/provider strings for branch guard checks."""
    return str(value or "").strip().lower().replace("/", "_")


def find_deprecated_runtime_tokens(values: Iterable[object]) -> list[str]:
    """Return deprecated tokens found in a runtime config value set."""
    findings: list[str] = []
    normalized_values = [normalize_runtime_token(value) for value in values]
    for value in normalized_values:
        for token in DEPRECATED_RUNTIME_TOKENS:
            normalized_token = normalize_runtime_token(token)
            if normalized_token and normalized_token in value:
                findings.append(token)
    return sorted(set(findings))


def assert_no_deprecated_runtime_tokens(values: Iterable[object]) -> None:
    """Fail fast when a deprecated model branch appears in active runtime config."""
    findings = find_deprecated_runtime_tokens(values)
    if findings:
        raise ValueError(
            "Deprecated RAG runtime branch is not allowed in "
            f"{ACTIVE_RAG_RUNTIME_PROFILE}: {', '.join(findings)}"
        )


def get_active_rag_runtime_profile() -> RagRuntimeProfile:
    """Return the only supported official RAG runtime profile."""
    return ACTIVE_PROFILE


def get_embedding_model_for_query_family(query_family: str | None) -> str:
    """Resolve the official retrieval embedding policy by query family."""
    family = str(query_family or "fact").strip().lower()
    if family in PRO_QUERY_FAMILIES:
        return ACTIVE_PROFILE.embedding_model_pro
    return ACTIVE_PROFILE.embedding_model_flash


def get_collection_for_stage(stage: str) -> str:
    """Resolve the canonical Milvus collection for a retrieval stage."""
    normalized = str(stage or "rule").strip().lower()
    return ACTIVE_PROFILE.collections.get(normalized, ACTIVE_PROFILE.collections["rule"])


def active_runtime_as_dict() -> dict[str, object]:
    """Serialize active runtime for reports and benchmark metadata."""
    return {
        "name": ACTIVE_PROFILE.name,
        "embedding_provider": ACTIVE_PROFILE.embedding_provider,
        "embedding_model_flash": ACTIVE_PROFILE.embedding_model_flash,
        "embedding_model_pro": ACTIVE_PROFILE.embedding_model_pro,
        "embedding_dimension": ACTIVE_PROFILE.embedding_dimension,
        "reranker_provider": ACTIVE_PROFILE.reranker_provider,
        "reranker_model": ACTIVE_PROFILE.reranker_model,
        "llm_provider": ACTIVE_PROFILE.llm_provider,
        "llm_model": ACTIVE_PROFILE.llm_model,
        "vector_store_backend": ACTIVE_PROFILE.vector_store_backend,
        "collections": dict(ACTIVE_PROFILE.collections),
    }
