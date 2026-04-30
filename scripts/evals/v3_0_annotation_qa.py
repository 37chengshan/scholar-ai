#!/usr/bin/env python3
"""Annotation QA checker for v3.0 academic benchmark corpus."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "v3_0_academic" / "corpus_public.json"

CLAIMS_REQUIRED_FAMILIES = {
    "compare",
    "cross_paper_synthesis",
    "numeric",
    "conflict_verification",
    "limitation",
}
HIGH_RISK_FAMILIES = {
    "numeric",
    "table",
    "figure",
    "formula",
    "conflict_verification",
    "no_answer",
}


def main() -> int:
    if not CORPUS.exists():
        print(f"missing corpus: {CORPUS}")
        return 1

    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    queries = payload.get("queries") or []

    failures: list[str] = []
    by_family = defaultdict(int)

    for q in queries:
        if not isinstance(q, dict):
            failures.append("query item must be an object")
            continue

        qid = str(q.get("query_id") or "unknown")
        family = str(q.get("family") or "")
        by_family[family] += 1
        must_abstain = bool(q.get("must_abstain", False))

        if family in CLAIMS_REQUIRED_FAMILIES and not must_abstain:
            claims = q.get("claims")
            if not isinstance(claims, list) or len(claims) == 0:
                failures.append(f"{qid}: required claims[] missing for family={family}")

        if family in HIGH_RISK_FAMILIES and not bool(q.get("reviewer_checked", False)):
            failures.append(f"{qid}: high-risk family requires reviewer_checked=true")

        if not must_abstain and not (q.get("expected_evidence") or []):
            failures.append(f"{qid}: answerable query must include expected_evidence")

    print(f"queries={len(queries)}")
    print(f"family_counts={dict(sorted(by_family.items()))}")

    if failures:
        print(f"qa_failed={len(failures)}")
        for item in failures[:30]:
            print(f"- {item}")
        return 1

    print("qa_passed=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
