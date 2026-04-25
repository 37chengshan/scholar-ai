"""RAG runtime profile contract for the API-first main chain.

This module intentionally avoids importing provider SDKs or local model runtimes.
It is a lightweight guard used by config, benchmark scripts, and tests to prevent
BGE/SPECTER2/local-Qwen lines from silently re-entering the default RAG path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


ACTIVE_RAG_RUNTIME_PROFILE = "api_flash_qwen_rerank_glm"

ACTIVE_EMBEDDING_PROVIDER = "tongyi"
ACTIVE_EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"

ACTIVE_RERANKER_PROVIDER = "qwen_api"
ACTIVE_RERANKER_MODEL = "qwen3-vl-rerank"

ACTIVE_LLM_PROVIDER = "zhipu"
ACTIVE_LLM_MODEL = "glm-4.5-air"

ACTIVE_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
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

    The profile is deliberately explicit: there is one production RAG runtime and
    any other branch must be treated as experimental/deprecated.
    """

    name: str
    embedding_provider: str
    embedding_model: str
    reranker_provider: str
    reranker_model: str
    llm_provider: str
    llm_model: str
    collections: Mapping[str, str]


ACTIVE_PROFILE = RagRuntimeProfile(
    name=ACTIVE_RAG_RUNTIME_PROFILE,
    embedding_provider=ACTIVE_EMBEDDING_PROVIDER,
    embedding_model=ACTIVE_EMBEDDING_MODEL,
    reranker_provider=ACTIVE_RERANKER_PROVIDER,
    reranker_model=ACTIVE_RERANKER_MODEL,
    llm_provider=ACTIVE_LLM_PROVIDER,
    llm_model=ACTIVE_LLM_MODEL,
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


def active_runtime_as_dict() -> dict[str, object]:
    """Serialize active runtime for reports and benchmark metadata."""
    return {
        "name": ACTIVE_PROFILE.name,
        "embedding_provider": ACTIVE_PROFILE.embedding_provider,
        "embedding_model": ACTIVE_PROFILE.embedding_model,
        "reranker_provider": ACTIVE_PROFILE.reranker_provider,
        "reranker_model": ACTIVE_PROFILE.reranker_model,
        "llm_provider": ACTIVE_PROFILE.llm_provider,
        "llm_model": ACTIVE_PROFILE.llm_model,
        "collections": dict(ACTIVE_PROFILE.collections),
    }
