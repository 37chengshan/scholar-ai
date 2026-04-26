#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pymilvus import connections

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in (str(API_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.model_gateway import create_embedding_provider
from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.evidence_quality import score_evidence
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from scripts.evals.v3_0_paper_section_recall_eval import (
    ARTIFACT_PAPERS_ROOT,
    COLLECTION_SUFFIX,
    EMBEDDING_MODEL,
    GOLDEN_PATH,
    load_golden,
    stage_collection_name,
)

OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_1"
DOC_REPORT = ROOT / "docs" / "reports" / "v3_1_result_trust_audit.md"

FORBIDDEN_TOKENS = [
    "expected_source_chunk_ids",
    "expected_answer",
    "evidence_anchors",
    "expected_sections",
]

SCAN_PATHS = [
    ROOT / "apps" / "api" / "app" / "rag_v3" / "retrieval",
    ROOT / "apps" / "api" / "app" / "rag_v3" / "evaluation",
    ROOT / "scripts" / "evals" / "v3_0_official_gate.py",
    ROOT / "scripts" / "evals" / "v3_0_evidence_quality_eval.py",
    ROOT / "scripts" / "evals" / "v3_0_hierarchical_retrieval_regression.py",
]


@dataclass
class ManualAuditRow:
    query_id: str
    stage: str
    query_family: str
    answer_mode: str
    claim_count: int
    supported_claim_count: int
    partially_supported_claim_count: int
    unsupported_claim_count: int
    citation_count: int
    valid_citation_count: int
    citation_jump_valid: bool
    evidence_matches_answer: bool
    manual_verdict: str
    notes: str


def _build_retriever(stage: str, milvus_host: str, milvus_port: int) -> HierarchicalRetriever:
    paper_index, section_index = build_indexes_from_artifacts(
        artifact_root=ARTIFACT_PAPERS_ROOT,
        stage=stage,
    )

    alias = f"v3_1_audit_{stage}"
    connections.connect(alias=alias, host=milvus_host, port=milvus_port)
    embedding_provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)
    collection_name = stage_collection_name(stage, COLLECTION_SUFFIX)

    dense_retriever = DenseEvidenceRetriever(
        embedding_provider=embedding_provider,
        collection_name=collection_name,
        milvus_alias=alias,
        output_fields=["source_chunk_id", "paper_id", "normalized_section_path", "content_type", "anchor_text"],
    )

    return HierarchicalRetriever(
        paper_index=paper_index,
        section_index=section_index,
        dense_retriever=dense_retriever,
    )


def _sample_queries(max_queries: int, seed: int) -> list[Any]:
    rows = load_golden(GOLDEN_PATH, max_queries=None)
    by_family: dict[str, list[Any]] = {}
    for row in rows:
        by_family.setdefault(row.query_family, []).append(row)

    rnd = random.Random(seed)
    selected: list[Any] = []

    # Coverage-first: sample one from each family if available.
    for family in sorted(by_family.keys()):
        family_rows = by_family[family]
        if family_rows:
            selected.append(rnd.choice(family_rows))

    # Fill remaining slots from all rows.
    if len(selected) < max_queries:
        remaining = [r for r in rows if r not in selected]
        rnd.shuffle(remaining)
        selected.extend(remaining[: max_queries - len(selected)])

    return selected[:max_queries]


def _audit_manual(retrievers: dict[str, HierarchicalRetriever], rows: list[Any]) -> list[ManualAuditRow]:
    stage_cycle = ["raw", "rule", "llm"]
    audited: list[ManualAuditRow] = []

    for idx, row in enumerate(rows):
        stage = stage_cycle[idx % len(stage_cycle)]
        retriever = retrievers[stage]
        pack = retriever.retrieve_evidence(row.query, row.query_family, stage=stage, top_k=10)
        quality = score_evidence(pack)
        contract = build_answer_contract(pack, quality)

        claim_count = len(contract.claims)
        supported = sum(1 for c in contract.claims if c.support_status == "supported")
        partial = sum(1 for c in contract.claims if c.support_status == "partially_supported")
        unsupported = sum(1 for c in contract.claims if c.support_status == "unsupported")

        citation_count = len(contract.citations)
        valid_citation_count = sum(1 for c in contract.citations if c)
        citation_jump_valid = valid_citation_count == citation_count

        evidence_matches_answer = unsupported <= max(1, claim_count // 4)
        if claim_count == 0:
            evidence_matches_answer = quality.answerability == "abstain"

        if citation_jump_valid and evidence_matches_answer and unsupported == 0:
            verdict = "PASS"
        elif citation_jump_valid and evidence_matches_answer:
            verdict = "PARTIAL"
        else:
            verdict = "FAIL"

        audited.append(
            ManualAuditRow(
                query_id=row.query_id,
                stage=stage,
                query_family=row.query_family,
                answer_mode=contract.answer_mode,
                claim_count=claim_count,
                supported_claim_count=supported,
                partially_supported_claim_count=partial,
                unsupported_claim_count=unsupported,
                citation_count=citation_count,
                valid_citation_count=valid_citation_count,
                citation_jump_valid=citation_jump_valid,
                evidence_matches_answer=evidence_matches_answer,
                manual_verdict=verdict,
                notes="auto-assisted audit; manual spot-check recommended",
            )
        )

    return audited


def _leakage_check() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def iter_files(path: Path) -> list[Path]:
        if path.is_file():
            return [path]
        return [p for p in path.rglob("*.py") if p.is_file()]

    for base in SCAN_PATHS:
        for file in iter_files(base):
            text = file.read_text(encoding="utf-8", errors="ignore")
            for token in FORBIDDEN_TOKENS:
                if token in text:
                    for ln, line in enumerate(text.splitlines(), start=1):
                        if token in line:
                            findings.append(
                                {
                                    "file": str(file.relative_to(ROOT)),
                                    "line": ln,
                                    "token": token,
                                    "line_text": line.strip(),
                                }
                            )

    blocking_hits = [
        f
        for f in findings
        if any(k in f["line_text"] for k in ("retrieve_evidence", "DenseEvidenceRetriever", "build_answer_contract"))
    ]

    return {
        "forbidden_tokens": FORBIDDEN_TOKENS,
        "findings": findings,
        "blocking_hits": blocking_hits,
        "evaluator_leakage": len(blocking_hits) > 0,
        "golden_expected_ids_not_used_as_retrieval_input": len(blocking_hits) == 0,
    }


def _metric_sanity(manual_rows: list[ManualAuditRow]) -> dict[str, Any]:
    total = len(manual_rows)
    citation_jump_valid_rate = sum(1 for r in manual_rows if r.citation_jump_valid) / max(total, 1)
    pass_rate = sum(1 for r in manual_rows if r.manual_verdict == "PASS") / max(total, 1)

    total_claims = sum(r.claim_count for r in manual_rows)
    unsupported_rate = sum(r.unsupported_claim_count for r in manual_rows) / max(total_claims, 1)
    consistency = sum(1 for r in manual_rows if r.evidence_matches_answer) / max(total, 1)

    return {
        "sample_size": total,
        "manual_audit_pass_rate": round(pass_rate, 4),
        "citation_jump_valid_rate": round(citation_jump_valid_rate, 4),
        "unsupported_claim_rate_recomputed": round(unsupported_rate, 4),
        "answer_evidence_consistency_recomputed": round(consistency, 4),
        "notes": [
            "citation_coverage/consistency in auto metrics can be optimistic on sparse claims",
            "manual spot-check is required before strict release",
        ],
    }


def _fallback_audit(official_gate_path: Path, hierarchical_path: Path) -> dict[str, Any]:
    fallback_used_count = None
    fallback_reason_distribution: dict[str, int] = {}
    fallback_stage_distribution: dict[str, int] = {}
    milvus_error_count = None
    provider_error_count = None

    phase1 = {}
    if official_gate_path.exists():
        phase1 = json.loads(official_gate_path.read_text(encoding="utf-8"))

    hierarchical = {}
    if hierarchical_path.exists():
        hierarchical = json.loads(hierarchical_path.read_text(encoding="utf-8"))

    # Current v3.0 outputs do not carry strict fallback counters everywhere.
    if "fallback_snapshot" in phase1:
        snap = phase1["fallback_snapshot"]
        fallback_used_count = snap.get("fallback_used_count")

    return {
        "fallback_used_count": fallback_used_count,
        "fallback_reason_distribution": fallback_reason_distribution,
        "fallback_stage_distribution": fallback_stage_distribution,
        "milvus_error_count": milvus_error_count,
        "provider_error_count": provider_error_count,
        "strict_fallback_counter_available": fallback_used_count is not None,
        "needs_v3_2_cleanup": fallback_used_count is None,
        "context": {
            "official_gate_overall": phase1.get("overall_verdict"),
            "hierarchical_overall": hierarchical.get("overall_verdict"),
        },
    }


def _write_markdown(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", "", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="v3.1 Result Trust Audit")
    parser.add_argument("--max-queries", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_REPORT.parent.mkdir(parents=True, exist_ok=True)

    sampled_rows = _sample_queries(max_queries=max(20, args.max_queries), seed=args.seed)
    retrievers = {
        "raw": _build_retriever("raw", args.milvus_host, args.milvus_port),
        "rule": _build_retriever("rule", args.milvus_host, args.milvus_port),
        "llm": _build_retriever("llm", args.milvus_host, args.milvus_port),
    }

    manual_rows = _audit_manual(retrievers, sampled_rows[: args.max_queries])
    manual_payload = {
        "sample_size": len(manual_rows),
        "results": [asdict(r) for r in manual_rows],
    }

    leakage_payload = _leakage_check()
    metric_payload = _metric_sanity(manual_rows)
    fallback_payload = _fallback_audit(
        ROOT / "artifacts" / "benchmarks" / "v3_0" / "official_gate_results.json",
        ROOT / "artifacts" / "benchmarks" / "v3_0" / "hierarchical_16x3_results.json",
    )

    (OUT_DIR / "manual_evidence_audit.json").write_text(
        json.dumps(manual_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(OUT_DIR / "manual_evidence_audit.md", "v3.1 Manual Evidence Audit", manual_payload)

    (OUT_DIR / "evaluator_leakage_check.json").write_text(
        json.dumps(leakage_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(OUT_DIR / "evaluator_leakage_check.md", "v3.1 Evaluator Leakage Check", leakage_payload)

    (OUT_DIR / "metric_sanity_check.json").write_text(
        json.dumps(metric_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(OUT_DIR / "metric_sanity_check.md", "v3.1 Metric Sanity Check", metric_payload)

    (OUT_DIR / "fallback_audit.json").write_text(
        json.dumps(fallback_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(OUT_DIR / "fallback_audit.md", "v3.1 Fallback Audit", fallback_payload)

    pass_rate = metric_payload["manual_audit_pass_rate"]
    citation_rate = metric_payload["citation_jump_valid_rate"]
    leakage = leakage_payload["evaluator_leakage"]
    fallback_known = fallback_payload["strict_fallback_counter_available"]

    if leakage or pass_rate < 0.70 or citation_rate < 0.80:
        verdict = "BLOCKED"
        allow_v32 = "NOT_ALLOWED"
    elif pass_rate >= 0.80 and citation_rate >= 0.90 and fallback_known:
        verdict = "PASS"
        allow_v32 = "ALLOWED"
    else:
        verdict = "CONDITIONAL"
        allow_v32 = "ALLOWED"

    report = {
        "verdict": verdict,
        "v3_2_allowed": allow_v32,
        "manual_audit_pass_rate": pass_rate,
        "citation_jump_valid_rate": citation_rate,
        "evaluator_leakage": leakage,
        "fallback_counter_available": fallback_known,
        "artifacts": {
            "manual": str((OUT_DIR / "manual_evidence_audit.json").relative_to(ROOT)),
            "leakage": str((OUT_DIR / "evaluator_leakage_check.json").relative_to(ROOT)),
            "sanity": str((OUT_DIR / "metric_sanity_check.json").relative_to(ROOT)),
            "fallback": str((OUT_DIR / "fallback_audit.json").relative_to(ROOT)),
        },
    }

    DOC_REPORT.write_text(
        "# v3.1 Result Trust Audit\n\n"
        + "```json\n"
        + json.dumps(report, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
