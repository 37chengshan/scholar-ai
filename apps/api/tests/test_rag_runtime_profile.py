import pytest

from app.core.rag_runtime_profile import (
    ACTIVE_COLLECTIONS,
    ACTIVE_EMBEDDING_MODEL_FLASH,
    ACTIVE_EMBEDDING_MODEL_PRO,
    ACTIVE_LLM_MODEL,
    ACTIVE_RAG_RUNTIME_PROFILE,
    ACTIVE_RERANKER_MODEL,
    active_runtime_as_dict,
    assert_no_deprecated_runtime_tokens,
    find_deprecated_runtime_tokens,
    get_active_rag_runtime_profile,
    get_embedding_model_for_query_family,
)


def test_active_runtime_profile_is_single_online_first_chain():
    profile = get_active_rag_runtime_profile()

    assert profile.name == "dashscope_qwen_online__qwen_rerank__glm_air"
    assert profile.embedding_provider == "dashscope_qwen"
    assert profile.embedding_model_flash == "qwen_flash"
    assert profile.embedding_model_pro == "qwen_pro"
    assert profile.reranker_provider == "dashscope_qwen"
    assert profile.reranker_model == "qwen_rerank"
    assert profile.llm_provider == "zhipu"
    assert profile.llm_model == "glm-4.5-air"
    assert profile.vector_store_backend == "milvus"
    assert profile.collections == ACTIVE_COLLECTIONS


def test_active_runtime_report_contract():
    payload = active_runtime_as_dict()

    assert payload["name"] == ACTIVE_RAG_RUNTIME_PROFILE
    assert payload["embedding_model_flash"] == ACTIVE_EMBEDDING_MODEL_FLASH
    assert payload["embedding_model_pro"] == ACTIVE_EMBEDDING_MODEL_PRO
    assert payload["reranker_model"] == ACTIVE_RERANKER_MODEL
    assert payload["llm_model"] == ACTIVE_LLM_MODEL
    assert payload["vector_store_backend"] == "milvus"
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
            ACTIVE_EMBEDDING_MODEL_FLASH,
            ACTIVE_EMBEDDING_MODEL_PRO,
            ACTIVE_RERANKER_MODEL,
            ACTIVE_LLM_MODEL,
            *ACTIVE_COLLECTIONS.values(),
        ]
    )


def test_query_family_policy_uses_flash_and_pro_tiers():
    assert get_embedding_model_for_query_family("fact") == ACTIVE_EMBEDDING_MODEL_FLASH
    assert get_embedding_model_for_query_family("compare") == ACTIVE_EMBEDDING_MODEL_PRO
