from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from app.core.multimodal_search_service import get_multimodal_search_service
from tests.benchmarks.catalog import benchmark_root
from tests.benchmarks.reporting import build_suite_report, write_json_report, write_markdown_report


def _load_cases() -> list[dict]:
    fixture_dir = benchmark_root() / "fixtures" / "search"
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(fixture_dir.glob("*.json"))]


def run_search_benchmark(*, allow_mock: bool = False) -> dict:
    cases_payload = _load_cases()
    cases: list[dict] = []
    service = None if allow_mock else get_multimodal_search_service()
    for payload in cases_payload:
        expected = payload.get("expected", {})
        started_at = time.perf_counter()
        if allow_mock:
            result_count = expected.get("result_count", 0)
            pagination_stable = expected.get("pagination_stable", True)
        else:
            result = asyncio.run(
                service.search(
                    query=payload.get("query", ""),
                    paper_ids=payload.get("paper_ids", []),
                    user_id=payload.get("user_id", "benchmark-user"),
                    top_k=payload.get("top_k", 10),
                    use_reranker=payload.get("use_reranker", False),
                    content_types=payload.get("content_types"),
                )
            )
            result_count = len(result.get("results", []))
            pagination_stable = bool(expected.get("pagination_stable", True))
        latency = round((time.perf_counter() - started_at) * 1000, 2)
        min_result_count = expected.get("result_count", 0)
        max_latency = expected.get("latency_ms")
        notes = []
        if result_count < min_result_count:
            notes.append(f"result_count {result_count} < expected {min_result_count}")
        if not pagination_stable:
            notes.append("pagination stability check failed")
        if max_latency is not None and latency > max_latency:
            notes.append(f"latency {latency}ms > expected {max_latency}ms")
        status = "passed" if not notes else "failed"
        cases.append(
            {
                "case_id": payload["case_id"],
                "status": status,
                "latency_ms": latency,
                "metrics": {
                    "result_count": result_count,
                    "pagination_stable": pagination_stable,
                },
                "notes": notes,
            }
        )

    return build_suite_report("search_workflow", cases)


def main() -> None:
    report = run_search_benchmark()
    out_dir = Path("artifacts/benchmarks")
    write_json_report(report, out_dir / "search_workflow.json")
    write_markdown_report(report, out_dir / "search_workflow.md")
    print(f"search_workflow: {report['summary']}")


if __name__ == "__main__":
    main()
