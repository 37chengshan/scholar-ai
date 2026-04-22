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
        input_payload = payload.get("input", {})
        expected = payload.get("expected", {})
        started_at = time.perf_counter()
        if allow_mock:
            result_count = expected.get("result_count", 0)
            pagination_stable = expected.get("pagination_stable", True)
            query_family = payload.get("query_family", "fact")
            planner_query_count = payload.get("planner_query_count", 1)
            decontextualized_query = input_payload.get("query", "")
            second_pass_used = bool(payload.get("second_pass_used", False))
            second_pass_gain = float(payload.get("second_pass_gain", 0.0))
            evidence_bundle_hit_count = int(payload.get("evidence_bundle_hit_count", 0))
            paper_role_hit_rate = float(payload.get("paper_role_hit_rate", 0.0))
            table_hit_rate = float(payload.get("table_hit_rate", 0.0))
            figure_hit_rate = float(payload.get("figure_hit_rate", 0.0))
            numeric_qa_exact_match = float(payload.get("numeric_qa_exact_match", 0.0))
            top5_cross_paper_completeness = float(payload.get("top5_cross_paper_completeness", 0.0))
        else:
            result = asyncio.run(
                service.search(
                    query=input_payload.get("query", ""),
                    paper_ids=input_payload.get("paper_ids", []),
                    user_id=input_payload.get("user_id", "benchmark-user"),
                    top_k=input_payload.get("top_k", 10),
                    use_reranker=input_payload.get("use_reranker", False),
                    content_types=input_payload.get("content_types"),
                )
            )
            result_count = len(result.get("results", []))
            pagination_stable = bool(expected.get("pagination_stable", True))
            query_family = result.get("query_family")
            planner_query_count = result.get("planner_query_count", 0)
            decontextualized_query = result.get("decontextualized_query")
            second_pass_used = bool(result.get("second_pass_used", False))
            second_pass_gain = float(result.get("second_pass_gain", 0.0))
            results = result.get("results", [])
            evidence_bundle_hit_count = len({r.get("evidence_bundle_id") for r in results[:10] if r.get("evidence_bundle_id")})
            top_results = results[:10]
            paper_role_hit_rate = (sum(1 for r in top_results if r.get("paper_role")) / len(top_results)) if top_results else 0.0
            table_hits = [r for r in top_results if r.get("table_ref")]
            figure_hits = [r for r in top_results if r.get("figure_ref")]
            table_hit_rate = (len(table_hits) / len(top_results)) if top_results else 0.0
            figure_hit_rate = (len(figure_hits) / len(top_results)) if top_results else 0.0
            numeric_qa_exact_match = 1.0 if any(r.get("score_value") is not None and r.get("metric_name") for r in top_results) else 0.0
            expected_cross_papers = set(expected.get("expected_paper_ids", []))
            actual_papers = {r.get("paper_id") for r in results[:5] if r.get("paper_id")}
            top5_cross_paper_completeness = (
                len(actual_papers & expected_cross_papers) / len(expected_cross_papers)
                if expected_cross_papers
                else 0.0
            )
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
                    "query_family": query_family,
                    "planner_query_count": planner_query_count,
                    "decontextualized_query": decontextualized_query,
                    "second_pass_used": second_pass_used,
                    "second_pass_gain": second_pass_gain,
                    "evidence_bundle_hit_count": evidence_bundle_hit_count,
                    "paper_role_hit_rate": round(paper_role_hit_rate, 4),
                    "table_hit_rate": round(table_hit_rate, 4),
                    "figure_hit_rate": round(figure_hit_rate, 4),
                    "numeric_qa_exact_match": round(numeric_qa_exact_match, 4),
                    "top5_cross_paper_completeness": round(top5_cross_paper_completeness, 4),
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
