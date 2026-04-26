"""Tests for official RAG runtime config defaults and validation."""

from __future__ import annotations

from importlib import reload



def _reload_settings(monkeypatch, **env):
    baseline = {
        "RAG_RUNTIME_PROFILE": "api_flash_qwen_rerank_glm",
        "EMBEDDING_PROVIDER": "tongyi",
        "EMBEDDING_MODEL": "tongyi-embedding-vision-flash-2026-03-06",
        "RERANKER_PROVIDER": "qwen_api",
        "RERANKER_MODEL": "qwen3-vl-rerank",
        "LLM_PROVIDER": "zhipu",
        "LLM_MODEL": "glm-4.5-air",
        "RETRIEVAL_MODEL_STACK": "manual",
        "SCIENTIFIC_TEXT_EMBEDDING_BACKEND": "none",
    }
    baseline.update(env)

    for key, value in baseline.items():
        monkeypatch.setenv(key, value)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import app.config as config_module

    config_module.get_settings.cache_clear()
    config_module = reload(config_module)
    return config_module.settings


def test_default_runtime_profile_is_official(monkeypatch):
    settings = _reload_settings(monkeypatch)

    assert settings.RAG_RUNTIME_PROFILE == "api_flash_qwen_rerank_glm"
    assert settings.EMBEDDING_PROVIDER == "tongyi"
    assert settings.EMBEDDING_MODEL == "tongyi-embedding-vision-flash-2026-03-06"
    assert settings.RERANKER_PROVIDER == "qwen_api"
    assert settings.RERANKER_MODEL == "qwen3-vl-rerank"
    assert settings.LLM_PROVIDER == "zhipu"
    assert settings.LLM_MODEL == "glm-4.5-air"


def test_validate_rag_runtime_settings_passes_for_defaults(monkeypatch):
    settings = _reload_settings(monkeypatch)
    report = settings.validate_rag_runtime_settings()

    assert report["status"] == "PASS"
    assert report["runtime_profile"] == "api_flash_qwen_rerank_glm"
