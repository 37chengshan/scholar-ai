import pytest

from app.core.rag_runtime_profile import (
    ACTIVE_COLLECTIONS,
    ACTIVE_EMBEDDING_MODEL,
    ACTIVE_LLM_MODEL,
    ACTIVE_RAG_RUNTIME_PROFILE,
    ACTIVE_RERANKER_MODEL,
    active_runtime_as_dict,
    assert_no_deprecated_runtime_tokens,
    find_deprecated_runtime_tokens,
    get_active_rag_runtime_profile,
)


def test_active_runtime_profile_is_single_api_first_chain():
    profile = get_active_rag_runtime_profile()

    assert profile.name == "api_flash_qwen_rerank_glm"
    assert profile.embedding_provider == "tongyi"
    assert profile.embedding_model == "tongyi-embedding-vision-flash-2026-03-06"
    assert profile.reranker_provider == "qwen_api"
    assert profile.reranker_model == "qwen3-vl-rerank"
    assert profile.llm_provider == "zhipu"
    assert profile.llm_model == "glm-4.5-air"
    assert profile.collections == ACTIVE_COLLECTIONS


def test_active_runtime_report_contract():
    payload = active_runtime_as_dict()

    assert payload["name"] == ACTIVE_RAG_RUNTIME_PROFILE
    assert payload["embedding_model"] == ACTIVE_EMBEDDING_MODEL
    assert payload["reranker_model"] == ACTIVE_RERANKER_MODEL
    assert payload["llm_model"] == ACTIVE_LLM_MODEL
    assert payload["collections"] == {
        "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
        "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
        "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
    }


def test_deprecated_runtime_tokens_are_detected():
    findings = find_deprecated_runtime_tokens(
        [
            "bge_dual",
            "paper_contents_v2_specter2_raw_v2_1",
            "academic_hybrid",
            "local_qwen_embedding",
        ]
    )

    assert "bge_dual" in findings
    assert "specter2" in findings
    assert "academic_hybrid" in findings
    assert "local_qwen_embedding" in findings


def test_deprecated_runtime_tokens_fail_fast():
    with pytest.raises(ValueError):
        assert_no_deprecated_runtime_tokens(["SCIENTIFIC_TEXT_EMBEDDING_BACKEND=specter2"])


def test_active_runtime_tokens_pass_guard():
    assert_no_deprecated_runtime_tokens(
        [
            ACTIVE_RAG_RUNTIME_PROFILE,
            ACTIVE_EMBEDDING_MODEL,
            ACTIVE_RERANKER_MODEL,
            ACTIVE_LLM_MODEL,
            *ACTIVE_COLLECTIONS.values(),
        ]
    )
