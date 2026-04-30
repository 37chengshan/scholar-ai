#!/usr/bin/env python3
"""Build v3.0 academic benchmark public/blind corpus assets.

This bootstrap script enforces the kickoff freeze quotas and writes assets to:
  apps/api/artifacts/benchmarks/v3_0_academic/

It preserves phase6 as v2.x frozen source by reading phase6 seeds only.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PHASE6_CORPUS = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "phase6" / "corpus.json"
OUT_DIR = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "v3_0_academic"

DATASET_VERSION = "v3.0-academic-p0"
TARGET_PAPER_COUNT = 200
TARGET_QUERY_COUNT = 0  # computed from frozen family quota

DISCIPLINE_QUOTA = {
    "computer_science": 50,
    "medicine": 40,
    "economics": 30,
    "mathematics": 30,
    "education": 30,
    "interdisciplinary": 20,
}

FAMILY_QUOTA = {
    "fact": 64,
    "method": 64,
    "experiment_result": 64,
    "numeric": 48,
    "table": 48,
    "figure": 48,
    "formula": 32,
    "limitation": 48,
    "compare": 48,
    "cross_paper_synthesis": 48,
    "citation_trace": 32,
    "kb_global": 48,
    "no_answer": 48,
    "conflict_verification": 48,
}

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

FAMILY_TO_MODALITY = {
    "table": "table",
    "figure": "figure",
    "formula": "formula",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _bootstrap_papers(phase6: dict[str, Any]) -> list[dict[str, Any]]:
    seed_papers = list(phase6.get("papers") or [])
    if not seed_papers:
        raise RuntimeError("phase6 corpus has no papers; cannot bootstrap v3 papers")

    papers: list[dict[str, Any]] = []
    pidx = 1
    discipline_items = list(DISCIPLINE_QUOTA.items())
    for discipline, count in discipline_items:
        for i in range(count):
            seed = seed_papers[(pidx - 1) % len(seed_papers)]
            subfield = f"{discipline}_subfield_{(i % 8) + 1:02d}"
            papers.append(
                {
                    "paper_id": f"v3p_{pidx:03d}",
                    "title": f"{seed.get('title', 'ScholarAI Benchmark Paper')} · {discipline.replace('_', ' ').title()} Study {i + 1}",
                    "discipline": discipline,
                    "subfield": subfield,
                    "year": 2015 + (pidx % 11),
                    "language": "en",
                    "source_path": f"public/{discipline}/paper_{pidx:03d}.pdf",
                    "pdf_source_type": "academic_pdf",
                    "scan_quality": ["clean", "normal", "noisy"][pidx % 3],
                    "layout_complexity": ["low", "medium", "high"][pidx % 3],
                    "table_density": ["low", "medium", "high"][pidx % 3],
                    "figure_density": ["low", "medium", "high"][((pidx + 1) % 3)],
                    "formula_density": ["low", "medium", "high"][((pidx + 2) % 3)],
                    "paper_length_bucket": ["short", "medium", "long"][pidx % 3],
                }
            )
            pidx += 1

    if len(papers) != TARGET_PAPER_COUNT:
        raise RuntimeError(f"paper bootstrap count mismatch: {len(papers)} != {TARGET_PAPER_COUNT}")
    return papers


def _expected_evidence(query_id: str, paper_id: str, family: str) -> list[dict[str, Any]]:
    evidence_type = FAMILY_TO_MODALITY.get(family, "text")
    return [
        {
            "evidence_id": f"{query_id}_e1",
            "paper_id": paper_id,
            "page_num": 1,
            "section_path": "introduction" if family in {"fact", "method"} else "results",
            "char_start": 0,
            "char_end": 180,
            "quote": f"Supporting snippet for {query_id} in family {family}.",
            "evidence_type": evidence_type,
            "support_role": "primary",
            "citation_target": f"{paper_id}#p1",
        }
    ]


def _claims(query_id: str, family: str) -> list[dict[str, Any]]:
    if family not in CLAIMS_REQUIRED_FAMILIES:
        return []
    return [
        {
            "claim_id": f"{query_id}_c1",
            "claim_text": f"Claim for {family} query {query_id}.",
            "support_required": True,
            "evidence_ids": [f"{query_id}_e1"],
            "support_level": "supports",
        }
    ]


def _query_record(idx: int, family: str, paper_ids: list[str], discipline: str) -> dict[str, Any]:
    query_id = f"v3q_{idx:04d}"
    must_abstain = family == "no_answer"
    expected_paper_ids = [] if must_abstain else paper_ids[:2]
    abstain_reason = "corpus_evidence_missing" if must_abstain else ""
    evidence = [] if must_abstain else _expected_evidence(query_id, expected_paper_ids[0], family)
    modality = FAMILY_TO_MODALITY.get(family, "text")

    return {
        "query_id": query_id,
        "question": f"[{family}] Academic benchmark question #{idx}",
        "family": family,
        "discipline": discipline,
        "difficulty": ["easy", "medium", "hard"][idx % 3],
        "answerability": "unanswerable" if must_abstain else "answerable",
        "paper_scope": "multi" if family in {"compare", "cross_paper_synthesis", "conflict_verification"} else "single",
        "gold_short_answer": "insufficient evidence" if must_abstain else f"Short answer for {query_id}",
        "gold_long_answer": "The corpus does not provide enough evidence to answer this query." if must_abstain else f"Long answer for {query_id} in family {family}.",
        "must_abstain": must_abstain,
        "abstain_reason": abstain_reason,
        "expected_paper_ids": expected_paper_ids,
        "expected_sections": [] if must_abstain else ["introduction", "results"],
        "expected_evidence": evidence,
        "claims": [] if must_abstain else _claims(query_id, family),
        "reviewer_checked": family in HIGH_RISK_FAMILIES,
        "modality": modality,
    }


def _bootstrap_queries(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_discipline: dict[str, list[str]] = {}
    for paper in papers:
        by_discipline.setdefault(paper["discipline"], []).append(str(paper["paper_id"]))

    disciplines = list(DISCIPLINE_QUOTA.keys())
    queries: list[dict[str, Any]] = []
    qidx = 1
    for family, count in FAMILY_QUOTA.items():
        for n in range(count):
            discipline = disciplines[(qidx + n) % len(disciplines)]
            paper_ids = by_discipline[discipline]
            queries.append(_query_record(qidx, family, paper_ids, discipline))
            qidx += 1

    target_query_count = sum(FAMILY_QUOTA.values())
    if len(queries) != target_query_count:
        raise RuntimeError(f"query bootstrap count mismatch: {len(queries)} != {target_query_count}")
    return queries


def _build_public_corpus(phase6: dict[str, Any]) -> dict[str, Any]:
    papers = _bootstrap_papers(phase6)
    queries = _bootstrap_queries(papers)
    return {
        "dataset_version": DATASET_VERSION,
        "version": DATASET_VERSION,
        "split": "public_dev",
        "paper_count": len(papers),
        "query_count": len(queries),
        "query_families": list(FAMILY_QUOTA.keys()),
        "discipline_quota": DISCIPLINE_QUOTA,
        "family_quota": FAMILY_QUOTA,
        "kickoff_freeze": {
            "formula_report_only": True,
            "claims_required_families": sorted(CLAIMS_REQUIRED_FAMILIES),
            "blind_owner": "ai-platform",
            "runner_owner": "ai-platform",
        },
        "papers": papers,
        "queries": queries,
    }


def _build_blind_corpus(public_corpus: dict[str, Any]) -> dict[str, Any]:
    blind_queries: list[dict[str, Any]] = []
    for query in public_corpus["queries"]:
        blind_queries.append(
            {
                **query,
                "gold_short_answer": "[HIDDEN_FOR_BLIND]",
                "gold_long_answer": "[HIDDEN_FOR_BLIND]",
                "expected_evidence": [],
                "claims": [],
            }
        )

    return {
        **public_corpus,
        "split": "blind_test",
        "queries": blind_queries,
        "blind_policy": {
            "score_only": True,
            "allow_sample_level_gold": False,
            "return_fields": ["aggregate_metrics", "failure_bucket_summary"],
        },
    }


def _build_manifest() -> dict[str, Any]:
    return {
        "benchmark": "v3_0_academic",
        "dataset_version": DATASET_VERSION,
        "runs": [],
    }


def _print_summary(corpus: dict[str, Any], name: str) -> None:
    fam = Counter(q.get("family") for q in corpus.get("queries", []))
    print(f"[{name}] papers={corpus.get('paper_count')} queries={corpus.get('query_count')}")
    print(f"[{name}] families={dict(sorted(fam.items()))}")


def main() -> int:
    phase6 = _load_json(PHASE6_CORPUS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    public_corpus = _build_public_corpus(phase6)
    blind_corpus = _build_blind_corpus(public_corpus)
    manifest = _build_manifest()

    _dump_json(OUT_DIR / "corpus_public.json", public_corpus)
    _dump_json(OUT_DIR / "corpus_blind.json", blind_corpus)
    _dump_json(OUT_DIR / "manifest.json", manifest)

    _print_summary(public_corpus, "public")
    _print_summary(blind_corpus, "blind")
    print(f"output={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
