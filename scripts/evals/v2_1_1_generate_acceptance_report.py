#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_1_20"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _status(schema_audit: dict[str, Any], preflight: dict[str, Any], smoke: dict[str, Any], answers: dict[str, dict[str, Any]]) -> str:
    if schema_audit.get("overall_status") != "PASS":
        return "BLOCKED"
    if preflight.get("overall_status") != "PASS":
        return "BLOCKED"
    if smoke.get("overall_status") != "PASS":
        return "BLOCKED"

    for stage in ("raw", "rule", "llm"):
        report = answers.get(stage, {})
        if not report:
            return "BLOCKED"
        if report.get("total_queries", 0) <= 0:
            return "BLOCKED"
        if report.get("failure_types", {}).get("retrieval_miss", 0) >= report.get("total_queries", 0):
            return "BLOCKED"

    return "PASS"


def _default_strategy(retrieval: dict[str, dict[str, Any]], answers: dict[str, dict[str, Any]]) -> str:
    scored: list[tuple[str, float]] = []
    for stage in ("raw", "rule", "llm"):
        r = retrieval.get(f"{stage}_on", {})
        a = answers.get(stage, {})
        score = (
            float(r.get("recall_at_10_avg") or 0.0) * 0.4
            + float(r.get("mrr_avg") or 0.0) * 0.2
            + float(r.get("ndcg_at_10_avg") or 0.0) * 0.2
            + float(a.get("answer_evidence_consistency_avg") or 0.0) * 0.2
        )
        scored.append((stage, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0] if scored else "llm"


def main() -> None:
    schema_audit = _load(OUT_DIR / "milvus_schema_audit.json")
    preflight = _load(OUT_DIR / "preflight_v2_1_1.json")
    smoke = _load(OUT_DIR / "answer_smoke_v2_1_1.json")

    retrieval = {
        "raw_on": _load(OUT_DIR / "retrieval_raw_on.json"),
        "rule_on": _load(OUT_DIR / "retrieval_rule_on.json"),
        "llm_on": _load(OUT_DIR / "retrieval_llm_on.json"),
    }

    answers = {
        "raw": _load(OUT_DIR / "answer_raw_v2_1_1.json"),
        "rule": _load(OUT_DIR / "answer_rule_v2_1_1.json"),
        "llm": _load(OUT_DIR / "answer_llm_v2_1_1.json"),
    }

    comparison = {
        "stages": {
            stage: {
                "citation_coverage_avg": answers.get(stage, {}).get("citation_coverage_avg", 0.0),
                "unsupported_claim_rate_avg": answers.get(stage, {}).get("unsupported_claim_rate_avg", 0.0),
                "answer_evidence_consistency_avg": answers.get(stage, {}).get("answer_evidence_consistency_avg", 0.0),
                "answer_latency_p95_ms": answers.get(stage, {}).get("answer_latency_p95_ms", 0.0),
            }
            for stage in ("raw", "rule", "llm")
        }
    }
    (OUT_DIR / "answer_comparison_v2_1_1.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    final_status = _status(schema_audit, preflight, smoke, answers)
    default_stage = _default_strategy(retrieval, answers)

    still_has_dim_error = any(
        "vector dimension mismatch" in str(err).lower()
        for stage in ("raw", "rule", "llm")
        for err in (answers.get(stage, {}).get("failure_types", {}) or {}).keys()
    ) or any(
        "vector dimension mismatch" in str(answers.get(stage, {}).get("blocked_reason", "")).lower()
        for stage in ("raw", "rule", "llm")
    )
    still_has_unsupported_field = any(
        "unsupported field type" in str(err).lower()
        for stage in ("raw", "rule", "llm")
        for err in (answers.get(stage, {}).get("failure_types", {}) or {}).keys()
    ) or any(
        "unsupported field type" in str(answers.get(stage, {}).get("blocked_reason", "")).lower()
        for stage in ("raw", "rule", "llm")
    ) or any(
        "unsupported field type" in str(err).lower()
        for err in (smoke.get("observed_errors") or [])
    )

    report_path = OUT_DIR / "v2_1_1_acceptance_report.md"
    lines: list[str] = []
    lines.append("# Academic RAG v2.1.1 Acceptance Report")
    lines.append("")
    lines.append("## 1. v2.1 原 BLOCKED 原因")
    lines.append("")
    lines.append("- Milvus vector dimension mismatch")
    lines.append("- Milvus Unsupported field type: 0")
    lines.append("- Answer/Citation benchmark 无法稳定跑完")
    lines.append("")
    lines.append("## 2. v2.1.1 修复项")
    lines.append("")
    lines.append("- 新增 collection schema audit（JSON/MD）")
    lines.append("- 新增 retrieval branch registry，强制 branch->collection 映射")
    lines.append("- 在 Milvus 搜索前增加 dim guard")
    lines.append("- 增加 safe output_fields 过滤与 minimal 降级")
    lines.append("- preflight 升级为 schema-aware gate")
    lines.append("- 增加 reranker 诊断字段（pre/post top ids、是否改序）")
    lines.append("")
    lines.append("## 3. Schema Audit 结果")
    lines.append("")
    lines.append(f"- overall_status: {schema_audit.get('overall_status', 'MISSING')}")
    lines.append("")
    lines.append("## 4. Preflight 结果")
    lines.append("")
    lines.append(f"- overall_status: {preflight.get('overall_status', 'MISSING')}")
    lines.append(f"- strict_schema: {preflight.get('strict_schema')}")
    lines.append(f"- safe_output_fields_only: {preflight.get('safe_output_fields_only')}")
    lines.append("")
    lines.append("## 5. Answer/Citation 执行状态")
    lines.append("")
    for stage in ("raw", "rule", "llm"):
        row = answers.get(stage, {})
        lines.append(
            f"- {stage}: total={row.get('total_queries', 0)}, "
            f"citation_coverage_avg={row.get('citation_coverage_avg', 0):.4f}, "
            f"answer_evidence_consistency_avg={row.get('answer_evidence_consistency_avg', 0):.4f}"
        )
    lines.append("")
    lines.append("## 6. Milvus 错误是否仍存在")
    lines.append("")
    lines.append(f"- vector dimension mismatch: {still_has_dim_error}")
    lines.append(f"- Unsupported field type: {still_has_unsupported_field}")
    lines.append("")
    lines.append("## 7. raw/rule/llm Answer 对照")
    lines.append("")
    lines.append("| stage | citation_coverage | unsupported_claim_rate | answer_evidence_consistency | latency_p95_ms |")
    lines.append("|---|---:|---:|---:|---:|")
    for stage in ("raw", "rule", "llm"):
        row = comparison["stages"][stage]
        lines.append(
            f"| {stage} | {row['citation_coverage_avg']:.4f} | {row['unsupported_claim_rate_avg']:.4f} | "
            f"{row['answer_evidence_consistency_avg']:.4f} | {row['answer_latency_p95_ms']:.2f} |"
        )
    lines.append("")
    lines.append("## 8. 是否可以扩 50 篇")
    lines.append("")
    lines.append(f"- 建议: {'可以进入 50 篇灰度' if final_status == 'PASS' else '暂不建议扩容'}")
    lines.append("")
    lines.append("## 9. 推荐默认主链策略")
    lines.append("")
    lines.append(f"- 推荐: {default_stage}")
    lines.append("")
    lines.append("## Final Verdict")
    lines.append("")
    lines.append(f"- v2.1.1: {final_status}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"v2_1_1_report={report_path}")
    print(f"final_status={final_status}")


if __name__ == "__main__":
    main()
