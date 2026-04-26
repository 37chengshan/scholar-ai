"""Tests for runtime guard blocking deprecated branches."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.rag_runtime_guard import validate_active_rag_runtime



def _base_settings() -> SimpleNamespace:
    return SimpleNamespace(
        RAG_RUNTIME_PROFILE="api_flash_qwen_rerank_glm",
        EMBEDDING_PROVIDER="tongyi",
        EMBEDDING_MODEL="tongyi-embedding-vision-flash-2026-03-06",
        RERANKER_PROVIDER="qwen_api",
        RERANKER_MODEL="qwen3-vl-rerank",
        LLM_PROVIDER="zhipu",
        LLM_MODEL="glm-4.5-air",
        RETRIEVAL_MODEL_STACK="manual",
        SCIENTIFIC_TEXT_EMBEDDING_BACKEND="none",
        GRAPH_RETRIEVAL_ENABLED=False,
        SCIENTIFIC_TEXT_BRANCH_ENABLED=False,
    )


def test_runtime_guard_passes_for_official_chain():
    report = validate_active_rag_runtime(_base_settings())
    assert report["status"] == "PASS"
    assert report["deprecated_branch_used"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("RETRIEVAL_MODEL_STACK", "bge_dual"),
        ("RETRIEVAL_MODEL_STACK", "qwen_dual"),
        ("SCIENTIFIC_TEXT_EMBEDDING_BACKEND", "specter2"),
        ("RETRIEVAL_MODEL_STACK", "academic_hybrid"),
    ],
)
def test_runtime_guard_blocks_deprecated_branches(field, value):
    settings = _base_settings()
    setattr(settings, field, value)

    report = validate_active_rag_runtime(settings)

    assert report["status"] == "BLOCKED"
    assert "Deprecated runtime branch detected" in report["blocked_reason"]
