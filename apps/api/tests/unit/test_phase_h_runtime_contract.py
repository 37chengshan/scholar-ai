from app.core.model_gateway import create_embedding_provider
from app.core.runtime_contract import (
    build_local_binding,
    build_shim_binding,
    build_vector_store_binding,
    normalize_runtime_mode,
)


def test_normalize_runtime_mode_defaults_to_online_for_unknown_values(monkeypatch):
    monkeypatch.setenv("RUNTIME_MODE", "mystery")
    assert normalize_runtime_mode("mystery") == "online"


def test_local_binding_marks_online_request_as_degraded():
    binding = build_local_binding(
        component="embedding",
        provider_name="qwen3vl",
        model="Qwen3-VL-Embedding-2B",
        dimension=2048,
        supports_multimodal=True,
        requested_mode="online",
    )

    assert binding.resolved_mode == "local"
    assert binding.is_degraded is True
    assert "requested online runtime" in binding.degraded_conditions[0]


def test_shim_provider_exposes_runtime_binding(monkeypatch):
    monkeypatch.setattr("app.core.model_gateway.dashscope_is_configured", lambda: False)
    provider = create_embedding_provider("tongyi", "tongyi-embedding-vision-flash-2026-03-06")
    binding = provider.get_runtime_binding()

    assert binding.resolved_mode == "shim"
    assert binding.provider_name == "tongyi"
    assert binding.dimension == 1024


def test_vector_store_binding_reports_lite_fallback():
    binding = build_vector_store_binding(
        backend="milvus",
        resolved_mode="lite",
        degraded_conditions=["switched to lite"],
        requested_mode="online",
    )

    assert binding.resolved_mode == "lite"
    assert binding.is_degraded is True
    assert binding.degraded_conditions == ("switched to lite",)


def test_dashscope_embedding_provider_selected_when_api_key_present(monkeypatch):
    monkeypatch.setattr("app.core.model_gateway.dashscope_is_configured", lambda: True)
    monkeypatch.setattr(
        "app.core.model_gateway.settings.DASHSCOPE_EMBEDDING_MODEL_FLASH",
        "text-embedding-v4",
    )
    provider = create_embedding_provider("dashscope_qwen", "qwen_flash")
    binding = provider.get_runtime_binding()

    assert binding.resolved_mode == "online"
    assert binding.provider_name == "dashscope_qwen"
    assert binding.model == "text-embedding-v4"
