#!/usr/bin/env python
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_1_20"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _p50_from_metrics(report: dict[str, Any]) -> float:
    values = report.get("metrics_raw", {}).get("latency_ms") or []
    if not values:
        return 0.0
    values = sorted(values)
    return float(values[len(values) // 2])


def _status(integrity: dict[str, Any], retrieval: dict[str, Any], answer: dict[str, Any]) -> str:
    if integrity.get("overall_status") != "PASS":
        return "BLOCKED"

    llm_r10 = float(retrieval["llm_on"].get("recall_at_10_avg") or 0.0)
    llm_mrr = float(retrieval["llm_on"].get("mrr_avg") or 0.0)
    consistency = float(answer["llm"].get("answer_evidence_consistency_avg") or 0.0)

    if llm_r10 < 0.70 or llm_mrr < 0.50:
        return "BLOCKED"
    if consistency < 0.45:
        return "CONDITIONAL"
    return "PASS"


def _default_strategy(retrieval: dict[str, Any], answer: dict[str, Any]) -> str:
    candidates = []
    for key in ("raw_on", "rule_on", "llm_on"):
        r = retrieval[key]
        collection = key.split("_")[0]
        score = (
            float(r.get("recall_at_10_avg") or 0.0) * 0.40
            + float(r.get("mrr_avg") or 0.0) * 0.25
            + float(r.get("ndcg_at_10_avg") or 0.0) * 0.20
            + (1.0 - min(float(r.get("latency_p95_ms") or 0.0) / 30000.0, 1.0)) * 0.15
        )
        answer_report = answer.get(collection, {})
        score += float(answer_report.get("answer_evidence_consistency_avg") or 0.0) * 0.10
        candidates.append((collection, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def main() -> None:
    integrity = _load(OUT_DIR / "integrity_report.json")
    golden_stats = _load(OUT_DIR / "golden_queries_acceptance_stats.json")

    retrieval = {
        "raw_on": _load(OUT_DIR / "retrieval_raw_on.json"),
        "raw_off": _load(OUT_DIR / "retrieval_raw_off.json"),
        "rule_on": _load(OUT_DIR / "retrieval_rule_on.json"),
        "rule_off": _load(OUT_DIR / "retrieval_rule_off.json"),
        "llm_on": _load(OUT_DIR / "retrieval_llm_on.json"),
        "llm_off": _load(OUT_DIR / "retrieval_llm_off.json"),
    }

    answer = {
        "raw": _load(OUT_DIR / "answer_raw.json"),
        "rule": _load(OUT_DIR / "answer_rule.json"),
        "llm": _load(OUT_DIR / "answer_llm.json"),
    }

    reranker_gain = {}
    for stage in ("raw", "rule", "llm"):
        on = retrieval[f"{stage}_on"]
        off = retrieval[f"{stage}_off"]
        reranker_gain[stage] = {
            "delta_recall_at_10": float(on.get("recall_at_10_avg") or 0.0) - float(off.get("recall_at_10_avg") or 0.0),
            "delta_mrr": float(on.get("mrr_avg") or 0.0) - float(off.get("mrr_avg") or 0.0),
            "delta_ndcg_at_10": float(on.get("ndcg_at_10_avg") or 0.0) - float(off.get("ndcg_at_10_avg") or 0.0),
        }

    consolidated_failures = Counter()
    for stage in ("raw", "rule", "llm"):
        consolidated_failures.update(answer[stage].get("failure_types") or {})

    final_status = _status(integrity, retrieval, answer)
    default_stage = _default_strategy(retrieval, answer)

    report_path = OUT_DIR / "v2_1_acceptance_report.md"
    lines: list[str] = []
    lines.append("# Academic RAG v2.1 Acceptance Report")
    lines.append("")
    lines.append(f"- Final Verdict: {final_status}")
    lines.append(f"- Golden Validation: {golden_stats.get('validation_status')}")
    lines.append(f"- Integrity Status: {integrity.get('overall_status')}")
    lines.append("")
    lines.append("## 1. Integrity")
    lines.append("")
    lines.append(f"- raw/rule/llm all 1451: {all(integrity['checks'][k]['count_ok'] for k in ['raw','rule','llm'])}")
    lines.append(f"- all 20 papers covered: {all(integrity['checks'][k]['paper_coverage_ok'] for k in ['raw','rule','llm'])}")
    lines.append(f"- source_chunk_id aligned: {integrity['alignment']['source_chunk_alignment_ok']}")
    lines.append("")
    lines.append("## 2. Retrieval (Overall)")
    lines.append("")
    lines.append("| stage | reranker | Recall@5 | Recall@10 | MRR | nDCG@10 | evidence_hit_rate | table_hit_rate | figure_hit_rate | cross_paper_hit_rate | p50_latency_ms | p95_latency_ms | second_pass_trigger_rate |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for stage in ("raw", "rule", "llm"):
        row = retrieval[f"{stage}_on"]
        lines.append(
            "| "
            f"{stage} | on | {row.get('recall_at_5_avg',0):.4f} | {row.get('recall_at_10_avg',0):.4f} | {row.get('mrr_avg',0):.4f} | {row.get('ndcg_at_10_avg',0):.4f} | "
            f"{row.get('chunk_hit_rate_avg',0):.4f} | {row.get('table_hit_rate_avg',0):.4f} | {row.get('figure_hit_rate_avg',0):.4f} | {row.get('cross_paper_recall_at_5',0):.4f} | "
            f"{_p50_from_metrics(row):.2f} | {row.get('latency_p95_ms',0):.2f} | {row.get('second_pass_used_rate',0):.4f} |"
        )

    lines.append("")
    lines.append("## 3. Retrieval by Query Family")
    lines.append("")
    for stage in ("raw", "rule", "llm"):
        lines.append(f"### {stage} (reranker on)")
        lines.append("")
        lines.append("| family | count | Recall@10 | nDCG@10 | paper_hit_rate | evidence_hit_rate |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        fam = retrieval[f"{stage}_on"].get("query_family_breakdown") or {}
        for family, values in sorted(fam.items()):
            lines.append(
                f"| {family} | {values.get('query_count',0)} | {values.get('recall_at_10_avg',0):.4f} | {values.get('ndcg_at_10_avg',0):.4f} | {values.get('paper_hit_rate_avg',0):.4f} | {values.get('chunk_hit_rate_avg',0):.4f} |"
            )
        lines.append("")

    lines.append("## 4. Reranker Gain")
    lines.append("")
    lines.append("| stage | delta Recall@10 | delta MRR | delta nDCG@10 |")
    lines.append("|---|---:|---:|---:|")
    for stage in ("raw", "rule", "llm"):
        gain = reranker_gain[stage]
        lines.append(
            f"| {stage} | {gain['delta_recall_at_10']:.4f} | {gain['delta_mrr']:.4f} | {gain['delta_ndcg_at_10']:.4f} |"
        )

    lines.append("")
    lines.append("## 5. Answer/Citation")
    lines.append("")
    lines.append("| stage | citation_coverage | unsupported_claim_rate | answerEvidenceConsistency | table_grounding_validity | figure_grounding_validity | citation_jump_validity | answer_latency_p50_ms | answer_latency_p95_ms |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for stage in ("raw", "rule", "llm"):
        row = answer[stage]
        lines.append(
            f"| {stage} | {row.get('citation_coverage_avg',0):.4f} | {row.get('unsupported_claim_rate_avg',0):.4f} | {row.get('answer_evidence_consistency_avg',0):.4f} | {row.get('table_grounding_validity',0):.4f} | {row.get('figure_grounding_validity',0):.4f} | {row.get('citation_jump_validity',0):.4f} | {row.get('answer_latency_p50_ms',0):.2f} | {row.get('answer_latency_p95_ms',0):.2f} |"
        )

    lines.append("")
    lines.append("## 6. Failure Attribution")
    lines.append("")
    lines.append("| failure_type | count |")
    lines.append("|---|---:|")
    for ftype, count in consolidated_failures.most_common():
        lines.append(f"| {ftype} | {count} |")

    lines.append("")
    lines.append("## 7. Release Recommendation")
    lines.append("")
    lines.append(f"- 扩到 50 篇: {'可以，建议先做 50 篇灰度' if final_status == 'PASS' else '暂不建议，先修复问题后再扩容'}")
    lines.append(f"- 默认使用策略: {default_stage}")

    issues = []
    if integrity.get("overall_status") != "PASS":
        issues.append("Integrity 未通过（计数/对齐不一致）")
    if golden_stats.get("validation_status") != "PASS":
        issues.append("Golden query 覆盖或字段规范需补齐")
    for stage in ("raw", "rule", "llm"):
        if answer[stage].get("unsupported_claim_rate_avg", 0) > 0.40:
            issues.append(f"{stage} unsupported_claim_rate 偏高")
    lines.append("- 需要先修复的问题:")
    if issues:
        for item in issues:
            lines.append(f"  - {item}")
    else:
        lines.append("  - 当前验收范围内无阻塞项")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"acceptance_report={report_path}")
    print(f"final_status={final_status}")


if __name__ == "__main__":
    main()
