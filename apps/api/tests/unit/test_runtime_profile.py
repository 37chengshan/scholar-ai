"""Runtime profile and AI startup mode tests."""

import os
from importlib import reload

import pytest


def _reload_config_with_env(monkeypatch, **env_vars):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    import app.config as config_module

    config_module.get_settings.cache_clear()
    config_module = reload(config_module)
    return config_module.settings


def test_runtime_profile_default_by_environment(monkeypatch):
    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="development",
    )
    assert settings.RUNTIME_PROFILE == "dev-lite"

    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="staging",
    )
    assert settings.RUNTIME_PROFILE == "dev-full"

    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="production",
    )
    assert settings.RUNTIME_PROFILE == "prod"


def test_runtime_profile_override(monkeypatch):
    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="development",
        RUNTIME_PROFILE="dev-full",
    )
    assert settings.RUNTIME_PROFILE == "dev-full"


def test_ai_startup_mode_resolved_from_profile(monkeypatch):
    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="development",
    )
    assert settings.AI_STARTUP_MODE == "lazy"

    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="production",
    )
    assert settings.AI_STARTUP_MODE == "eager"

    settings = _reload_config_with_env(
        monkeypatch,
        ENVIRONMENT="staging",
        AI_STARTUP_MODE="off",
    )
    assert settings.AI_STARTUP_MODE == "off"
