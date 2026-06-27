from __future__ import annotations

from app.config import Settings


def test_allowed_hosts_accepts_json_string() -> None:
    settings = Settings(ALLOWED_HOSTS='["https://app.example.com", "http://localhost:5173"]')

    assert settings.ALLOWED_HOSTS == [
        "https://app.example.com",
        "http://localhost:5173",
    ]


def test_allowed_hosts_accepts_comma_separated_string() -> None:
    settings = Settings(ALLOWED_HOSTS="https://app.example.com, http://localhost:5173")

    assert settings.ALLOWED_HOSTS == [
        "https://app.example.com",
        "http://localhost:5173",
    ]


def test_allowed_hosts_ignores_empty_comma_segments() -> None:
    settings = Settings(ALLOWED_HOSTS="https://app.example.com,, ")

    assert settings.ALLOWED_HOSTS == ["https://app.example.com"]


def test_runtime_mode_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_MODE", "lite")

    settings = Settings()

    assert settings.RUNTIME_MODE == "lite"
