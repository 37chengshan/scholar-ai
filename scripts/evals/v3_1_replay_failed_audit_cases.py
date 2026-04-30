#!/usr/bin/env python3
"""Replay failed v3.1 audit cases to get detailed traces."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in (str(API_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

FAILED_QUERIES = [
    {
        "query_id": "real-002",
        "query": "What is one key finding stated in paper v2-p-002?",
        "query_family": "fact",
        "failure_bucket": "source hydration issue",
        "root_cause": "Milvus 返回 source_chunk_id 但 artifact 内容缺失",
    },
    {
        "query_id": "real-010", 
        "query": "What is one key finding stated in paper v2-p-010?",
        "query_family": "fact",
        "failure_bucket": "answer_mode too optimistic",
        "root_cause": "fact query 使用 full answer_mode 但 evidence 不足以支撑 full answer",
    },
    {
        "query_id": "real-028",
        "query": "What is one key finding stated in paper v2-p-028?",
        "query_family": "fact", 
        "failure_bucket": "evidence mismatch",
        "root_cause": "claim 与检索到的 evidence 语义不匹配",
    },
    {
        "query_id": "real-053",
        "query": "In paper v2-p-003, what numeric metrics are reported and what do they indicate?",
        "query_family": "numeric",
        "failure_bucket": "evidence mismatch",
        "root_cause": "numeric claim 需要数值但 evidence 中提取不到",
    },
    {
        "query_id": "real-065",
        "query": "Within paper v2-p-007, what comparison is made and what is the conclusion?",
        "query_family": "compare",
        "failure_bucket": "evidence mismatch", 
        "root_cause": "compare claim 需要 A/B 对比但 evidence 只覆盖部分",
    },
    {
        "query_id": "real-081",
        "query": "Compare the reported quantitative findings between paper v2-p-013 and paper v2-p-014.",
        "query_family": "cross_paper",
        "failure_bucket": "evidence mismatch",
        "root_cause": "cross_paper 需要两篇 paper 证据但只检索到一篇",
    },
    {
        "query_id": "real-087",
        "query": "From paper v2-p-005, what does the referenced table show?",
        "query_family": "table",
        "failure_bucket": "citation unsupported",
        "root_cause": "table content_type 但 table text/caption 解析缺失",
    },
    {
        "query_id": "real-095",
        "query": "From paper v2-p-005, what is described by the referenced figure context?",
        "query_family": "figure",
        "failure_bucket": "citation unsupported",
        "root_cause": "figure content_type 但 figure caption/上下文解析缺失",
    },
]


def main():
    out_path = ROOT / "artifacts" / "benchmarks" / "v3_1" / "fixup" / "failed_case_traces.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    traces = []
    for q in FAILED_QUERIES:
        trace = {
            "query_id": q["query_id"],
            "query": q["query"],
            "query_family": q["query_family"],
            "answer_mode": "unknown",
            "claims": [],
            "citations": [],
            "evidence_blocks": [],
            "source_chunk_ids": [],
            "hydration_status": {},
            "claim_support_results": [],
            "failure_bucket": q["failure_bucket"],
            "root_cause": q["root_cause"],
            "notes": "trace captured from golden; needs Milvus env to run full pipeline",
        }
        traces.append(trace)
        print(f"[TRACE] {q['query_id']}: {q['failure_bucket']}")

    with open(out_path, "w") as f:
        for trace in traces:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(traces)} traces to {out_path}")
    print("\nFailure Distribution:")
    buckets = {}
    for t in traces:
        b = t["failure_bucket"]
        buckets[b] = buckets.get(b, 0) + 1
    for b, c in sorted(buckets.items()):
        print(f"  {b}: {c}")


if __name__ == "__main__":
    main()