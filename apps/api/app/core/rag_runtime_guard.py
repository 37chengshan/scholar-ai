"""Runtime guard for validating active RAG configuration at startup/benchmark."""

from __future__ import annotations

from typing import Any

from app.core.rag_runtime_profile import (
    RagRuntimeValidationError,
    validate_runtime_contract,
)


def _collect_additional_runtime_values(settings: Any) -> dict[str, Any]:
    """Collect values that must never influence official runtime selection."""
    values: dict[str, Any] = {
        "RETRIEVAL_MODEL_STACK": getattr(settings, "RETRIEVAL_MODEL_STACK", None),
        "SCIENTIFIC_TEXT_EMBEDDING_BACKEND": getattr(
            settings, "SCIENTIFIC_TEXT_EMBEDDING_BACKEND", None
        ),
    }

    if bool(getattr(settings, "GRAPH_RETRIEVAL_ENABLED", False)):
        values["GRAPH_RETRIEVAL_ENABLED"] = "graph_branch"
    if bool(getattr(settings, "SCIENTIFIC_TEXT_BRANCH_ENABLED", False)):
        values["SCIENTIFIC_TEXT_BRANCH_ENABLED"] = "specter2"

    return values


def validate_active_rag_runtime(settings: Any, *, strict: bool = False) -> dict[str, Any]:
    """Validate active runtime and return runtime report.

    Args:
        settings: Settings-like object
        strict: when True, raise RuntimeError on blocked status
    """
    try:
        report = validate_runtime_contract(
            runtime_profile=getattr(settings, "RAG_RUNTIME_PROFILE", ""),
            embedding_provider=getattr(settings, "EMBEDDING_PROVIDER", ""),
            embedding_model=getattr(settings, "EMBEDDING_MODEL", ""),
            reranker_provider=getattr(settings, "RERANKER_PROVIDER", ""),
            reranker_model=getattr(settings, "RERANKER_MODEL", ""),
            llm_provider=getattr(settings, "LLM_PROVIDER", ""),
            llm_model=getattr(settings, "LLM_MODEL", ""),
            additional_values=_collect_additional_runtime_values(settings),
        )
        return report
    except RagRuntimeValidationError as exc:
        blocked = {
            "runtime_profile": getattr(settings, "RAG_RUNTIME_PROFILE", None),
            "embedding_model": getattr(settings, "EMBEDDING_MODEL", None),
            "reranker_model": getattr(settings, "RERANKER_MODEL", None),
            "llm_model": getattr(settings, "LLM_MODEL", None),
            "deprecated_branch_used": True,
            "status": "BLOCKED",
            "blocked_reason": str(exc),
        }
        if strict:
            raise RuntimeError(blocked["blocked_reason"]) from exc
        return blocked
