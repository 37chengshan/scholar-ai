#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean


def safe_rate(num: int, den: int) -> float:
    return round((num / den) if den else 0.0, 4)


def avg(values):
    return round(mean(values), 4) if values else 0.0


def is_import_case(case_id: str) -> bool:
    return case_id.startswith("IMP-")


def is_rag_case(case_id: str) -> bool:
    return case_id.startswith("RAG-")


def summarize(results):
    import_cases = [r for r in results if is_import_case(r.get("case_id", ""))]
    rag_cases = [r for r in results if is_rag_case(r.get("case_id", ""))]

    import_pass = sum(1 for r in import_cases if r.get("pass_fail") == "pass")
    import_query_ready_durations = [
        r.get("duration_ms", 0)
        for r in import_cases
        if r.get("query_ready") is True
    ]
    import_awaiting = sum(1 for r in import_cases if r.get("final_status") == "awaiting_user_action")

    resume_cases = [r for r in import_cases if r.get("case_id") in {"IMP-003"}]
    resume_success = sum(1 for r in resume_cases if r.get("pass_fail") == "pass")

    import_fail_reasons = Counter(
        r.get("failure_reason", "UNKNOWN")
        for r in import_cases
        if r.get("pass_fail") == "fail"
    )

    import_fallback_depth_values = [r.get("fallback_depth", 0) for r in import_cases]

    rag_citation_present = sum(1 for r in rag_cases if r.get("citation_present") is True)
    rag_low_conf = sum(1 for r in rag_cases if r.get("low_confidence_flag") is True)
    rag_consistency = [r.get("answer_evidence_consistency", 0.0) for r in rag_cases]
    rag_no_valid_sources = sum(1 for r in rag_cases if r.get("no_valid_sources") is True)

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.get("pass_fail") == "pass")

    summary = {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_case_ids": [r.get("case_id") for r in results if r.get("pass_fail") != "pass"],
        "metrics": {
            "import_success_rate": safe_rate(import_pass, len(import_cases)),
            "time_to_query_ready_ms": avg(import_query_ready_durations),
            "awaiting_user_action_rate": safe_rate(import_awaiting, len(import_cases)),
            "upload_resume_success_rate": safe_rate(resume_success, len(resume_cases)),
            "source_failure_breakdown": dict(import_fail_reasons),
            "fallback_depth": {
                "avg": avg(import_fallback_depth_values),
                "distribution": dict(Counter(import_fallback_depth_values)),
            },
            "citation_coverage_rate": safe_rate(rag_citation_present, len(rag_cases)),
            "low_confidence_rate": safe_rate(rag_low_conf, len(rag_cases)),
            "answer_evidence_consistency_avg": avg(rag_consistency),
            "no_valid_sources_rate": safe_rate(rag_no_valid_sources, len(rag_cases)),
        },
    }
    return summary


def write_markdown(summary, out_md: Path):
    m = summary["metrics"]
    lines = [
        "# vNext+1 验证结果汇总",
        "",
        f"- total_cases: {summary['total_cases']}",
        f"- passed_cases: {summary['passed_cases']}",
        f"- failed_case_ids: {', '.join(summary['failed_case_ids']) if summary['failed_case_ids'] else 'none'}",
        "",
        "## Import 指标",
        "",
        f"- import_success_rate: {m['import_success_rate']}",
        f"- time_to_query_ready_ms: {m['time_to_query_ready_ms']}",
        f"- awaiting_user_action_rate: {m['awaiting_user_action_rate']}",
        f"- upload_resume_success_rate: {m['upload_resume_success_rate']}",
        f"- source_failure_breakdown: {json.dumps(m['source_failure_breakdown'], ensure_ascii=False)}",
        f"- fallback_depth.avg: {m['fallback_depth']['avg']}",
        f"- fallback_depth.distribution: {json.dumps(m['fallback_depth']['distribution'], ensure_ascii=False)}",
        "",
        "## RAG 指标",
        "",
        f"- citation_coverage_rate: {m['citation_coverage_rate']}",
        f"- low_confidence_rate: {m['low_confidence_rate']}",
        f"- answer_evidence_consistency_avg: {m['answer_evidence_consistency_avg']}",
        f"- no_valid_sources_rate: {m['no_valid_sources_rate']}",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize vNext+1 validation results")
    parser.add_argument("--input", required=True, help="Path to validation results JSON")
    parser.add_argument("--output-json", required=True, help="Path to output summary JSON")
    parser.add_argument("--output-md", required=True, help="Path to output summary Markdown")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    summary = summarize(results)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(summary, output_md)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
