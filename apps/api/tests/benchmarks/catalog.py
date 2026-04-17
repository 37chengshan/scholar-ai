from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    domain: str
    title: str
    fixture_path: str
    tags: tuple[str, ...]
    expected_assertions: dict[str, Any]
    severity: str = "medium"


CATALOG: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        case_id="chat.simple",
        domain="chat",
        title="Simple chat round",
        fixture_path="fixtures/chat/simple_chat.json",
        tags=("chat", "stability"),
        expected_assertions={"stream_success": True},
        severity="medium",
    ),
    BenchmarkCase(
        case_id="search.empty",
        domain="search",
        title="Empty search query result",
        fixture_path="fixtures/search/empty_search.json",
        tags=("search", "empty"),
        expected_assertions={"allow_zero_results": True},
        severity="low",
    ),
    BenchmarkCase(
        case_id="rag.compare",
        domain="rag",
        title="Cross-paper compare",
        fixture_path="fixtures/rag/rag_compare.json",
        tags=("rag", "quality"),
        expected_assertions={"min_source_count": 1},
        severity="high",
    ),
    BenchmarkCase(
        case_id="import.flow",
        domain="import",
        title="Import job full flow",
        fixture_path="fixtures/import/import_flow.json",
        tags=("kb", "import"),
        expected_assertions={"terminal_status": "completed"},
        severity="high",
    ),
)


def benchmark_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_fixture(fixture_path: str) -> Path:
    return benchmark_root() / fixture_path


def list_cases(domain: str | None = None) -> list[BenchmarkCase]:
    if domain is None:
        return list(CATALOG)
    return [case for case in CATALOG if case.domain == domain]
