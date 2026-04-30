from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from app.config import settings

RuntimeMode = Literal["online", "local", "shim", "lite", "mixed"]


@dataclass(frozen=True)
class RuntimeBinding:
    component: str
    requested_mode: RuntimeMode
    resolved_mode: RuntimeMode
    provider_name: str
    provider_kind: str
    model: str
    dimension: int | None = None
    supports_multimodal: bool | None = None
    degraded_conditions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_degraded(self) -> bool:
        return self.requested_mode != self.resolved_mode or bool(self.degraded_conditions)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["degraded_conditions"] = list(self.degraded_conditions)
        payload["is_degraded"] = self.is_degraded
        return payload


def normalize_runtime_mode(raw_mode: str | None = None) -> RuntimeMode:
    mode = str(raw_mode or settings.RUNTIME_MODE or "online").strip().lower()
    if mode in {"online", "local", "shim", "lite", "mixed"}:
        return mode  # type: ignore[return-value]
    return "online"


def build_online_binding(
    *,
    component: str,
    provider_name: str,
    model: str,
    dimension: int | None,
    supports_multimodal: bool | None = None,
    requested_mode: RuntimeMode | None = None,
) -> RuntimeBinding:
    requested = requested_mode or normalize_runtime_mode()
    degraded: tuple[str, ...] = ()
    if requested in {"local", "shim", "lite"}:
        degraded = (
            f"{component} requested {requested} runtime, but resolved to online provider {provider_name}",
        )
    return RuntimeBinding(
        component=component,
        requested_mode=requested,
        resolved_mode="online",
        provider_name=provider_name,
        provider_kind="api_provider",
        model=model,
        dimension=dimension,
        supports_multimodal=supports_multimodal,
        degraded_conditions=degraded,
    )


def build_local_binding(
    *,
    component: str,
    provider_name: str,
    model: str,
    dimension: int | None,
    supports_multimodal: bool | None = None,
    requested_mode: RuntimeMode | None = None,
) -> RuntimeBinding:
    requested = requested_mode or normalize_runtime_mode()
    degraded: tuple[str, ...] = ()
    if requested == "online":
        degraded = (
            f"{component} requested online runtime, but resolved to local provider {provider_name}",
        )
    return RuntimeBinding(
        component=component,
        requested_mode=requested,
        resolved_mode="local",
        provider_name=provider_name,
        provider_kind="local_model",
        model=model,
        dimension=dimension,
        supports_multimodal=supports_multimodal,
        degraded_conditions=degraded,
    )


def build_shim_binding(
    *,
    component: str,
    provider_name: str,
    model: str,
    dimension: int | None,
    requested_mode: RuntimeMode | None = None,
) -> RuntimeBinding:
    requested = requested_mode or normalize_runtime_mode()
    return RuntimeBinding(
        component=component,
        requested_mode=requested,
        resolved_mode="shim",
        provider_name=provider_name,
        provider_kind="deterministic_shim",
        model=model,
        dimension=dimension,
        supports_multimodal=False,
        degraded_conditions=(
            f"{component} is served by deterministic shim provider {provider_name}",
        ),
    )


def build_vector_store_binding(
    *,
    backend: str,
    resolved_mode: RuntimeMode,
    degraded_conditions: list[str] | tuple[str, ...] | None = None,
    requested_mode: RuntimeMode | None = None,
) -> RuntimeBinding:
    requested = requested_mode or normalize_runtime_mode()
    return RuntimeBinding(
        component="vector_store",
        requested_mode=requested,
        resolved_mode=resolved_mode,
        provider_name=backend,
        provider_kind="vector_backend",
        model=backend,
        dimension=None,
        supports_multimodal=None,
        degraded_conditions=tuple(degraded_conditions or ()),
    )
