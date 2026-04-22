from __future__ import annotations

from pathlib import Path

from tests.benchmarks.reporting import build_suite_report, write_markdown_report


def test_build_suite_report_includes_threshold_verdict() -> None:
    report = build_suite_report(
        "search_workflow",
        [
            {
                "case_id": "search.basic",
                "status": "failed",
                "latency_ms": 3200,
                "query_family": "fact",
                "metrics": {
                    "query_family": "fact",
                    "planner_query_count": 2,
                    "second_pass_used": 0.0,
                    "second_pass_gain": 0.0,
                    "evidence_bundle_hit_count": 1,
                    "paper_role_hit_rate": 1.0,
                    "table_hit_rate": 0.0,
                    "figure_hit_rate": 0.0,
                    "numeric_qa_exact_match": 0.0,
                    "top5_cross_paper_completeness": 0.0,
                },
                "notes": [],
            }
        ],
    )

    assert report["summary"]["threshold_passed"] is False
    assert report["summary"]["threshold_errors"]
    assert report["summary"]["family_metrics"]["fact"]["cases"] == 1
    assert report["summary"]["family_metrics"]["fact"]["planner_query_count_avg"] == 2.0


def test_write_markdown_report_includes_family_summary(tmp_path: Path) -> None:
    report = build_suite_report(
        "search_workflow",
        [
            {
                "case_id": "search.basic",
                "status": "passed",
                "latency_ms": 180,
                "query_family": "fact",
                "metrics": {
                    "query_family": "fact",
                    "planner_query_count": 2,
                    "second_pass_used": 0.0,
                    "second_pass_gain": 0.0,
                    "evidence_bundle_hit_count": 1,
                    "paper_role_hit_rate": 1.0,
                    "table_hit_rate": 0.0,
                    "figure_hit_rate": 0.0,
                    "numeric_qa_exact_match": 0.0,
                    "top5_cross_paper_completeness": 0.0,
                },
                "notes": [],
            }
        ],
    )

    output_path = tmp_path / "search_workflow.md"
    write_markdown_report(report, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## Threshold Check" in content
    assert "## Query Family Summary" in content
    assert "fact: cases=1" in content
