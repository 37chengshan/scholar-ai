#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pymilvus import Collection, connections, utility

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evals.v2_4_common import (
    DEFAULT_ARTIFACT_ROOT,
    collect_paper_artifacts,
    read_json,
    source_chunk_set,
    stage_collection_name,
    write_json,
    write_markdown,
)

DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_5"

NUMERIC_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|kpc|km|ev|kev|mev|gev|dex|sigma|ms|hz|ghz|mhz)?\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.5 real golden corpus audit")
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--manifest", default=str(ROOT / "tests" / "evals" / "fixtures" / "papers" / "manifest.json"))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _load_manifest_paper_ids(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    papers = payload.get("papers", []) if isinstance(payload, dict) else []
    return {str(p.get("paper_id") or "") for p in papers if str(p.get("paper_id") or "")}


def _collection_stats(alias: str, name: str) -> Dict[str, Any]:
    if not utility.has_collection(name, using=alias):
        return {
            "name": name,
            "exists": False,
            "entity_count": 0,
            "paper_ids": set(),
            "source_chunk_ids": set(),
            "errors": ["collection_missing"],
        }

    col = Collection(name, using=alias)
    col.load()
    rows = col.query(expr="id >= 0", output_fields=["paper_id", "source_chunk_id"], limit=16384)
    paper_ids = {str(r.get("paper_id") or "") for r in rows if str(r.get("paper_id") or "")}
    source_ids = {str(r.get("source_chunk_id") or "") for r in rows if str(r.get("source_chunk_id") or "")}
    return {
        "name": name,
        "exists": True,
        "entity_count": int(col.num_entities),
        "paper_ids": paper_ids,
        "source_chunk_ids": source_ids,
        "errors": [],
    }


def _evidence_distribution(raw_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    content_types = Counter()
    table_like = 0
    figure_like = 0
    numeric_like = 0

    for chunk in raw_chunks:
        ctype = str(chunk.get("content_type") or "")
        content_types[ctype] += 1

        text = f"{chunk.get('content_data') or ''} {chunk.get('anchor_text') or ''}".strip()
        lower = text.lower()
        if ctype == "table" or "table" in lower:
            table_like += 1
        if ctype in {"figure", "caption", "page"} or "figure" in lower or "fig." in lower:
            figure_like += 1
        if NUMERIC_PATTERN.search(text):
            numeric_like += 1

    return {
        "content_types": dict(content_types),
        "table_like_chunks": table_like,
        "figure_like_chunks": figure_like,
        "numeric_like_chunks": numeric_like,
    }


def main() -> int:
    args = parse_args()
    artifact_root = Path(args.artifact_root)
    manifest_path = Path(args.manifest)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "artifact_root": str(artifact_root),
        "manifest_path": str(manifest_path),
        "checks": [],
        "paper_count": {},
        "stage_counts": {},
        "id_alignment": {},
        "evidence_distribution": {},
        "coverage_capability": {},
        "status": "BLOCKED",
        "error": None,
    }

    errors: List[str] = []

    try:
        manifest_ids = _load_manifest_paper_ids(manifest_path)
        artifacts = collect_paper_artifacts(artifact_root)
        paper_ids = {p.paper_id for p in artifacts}

        parse_ok = 0
        raw_ok = 0
        rule_ok = 0
        llm_ok = 0

        raw_all: List[Dict[str, Any]] = []
        raw_by_paper: Dict[str, Set[str]] = {}
        rule_by_paper: Dict[str, Set[str]] = {}
        llm_by_paper: Dict[str, Set[str]] = {}

        for art in artifacts:
            if art.parse_artifact_path.exists():
                parse_ok += 1
            raw_chunks = read_json(art.chunks_raw_path) if art.chunks_raw_path.exists() else []
            rule_chunks = read_json(art.chunks_rule_path) if art.chunks_rule_path.exists() else []
            llm_chunks = read_json(art.chunks_llm_path) if art.chunks_llm_path.exists() else []

            if art.chunks_raw_path.exists():
                raw_ok += 1
            if art.chunks_rule_path.exists():
                rule_ok += 1
            if art.chunks_llm_path.exists():
                llm_ok += 1

            raw_all.extend(raw_chunks)
            raw_by_paper[art.paper_id] = source_chunk_set(raw_chunks)
            rule_by_paper[art.paper_id] = source_chunk_set(rule_chunks)
            llm_by_paper[art.paper_id] = source_chunk_set(llm_chunks)

        report["paper_count"] = {
            "manifest": len(manifest_ids),
            "parse_artifacts": parse_ok,
            "chunk_artifacts_raw": raw_ok,
            "chunk_artifacts_rule": rule_ok,
            "chunk_artifacts_llm": llm_ok,
            "artifact_dirs": len(artifacts),
        }

        if len(manifest_ids) != 50:
            errors.append(f"manifest_paper_count_mismatch:{len(manifest_ids)}!=50")
        if parse_ok != 50:
            errors.append(f"parse_artifact_paper_count_mismatch:{parse_ok}!=50")
        if raw_ok != 50 or rule_ok != 50 or llm_ok != 50:
            errors.append("chunk_artifact_paper_count_mismatch")

        if manifest_ids and paper_ids != manifest_ids:
            errors.append("paper_id_set_mismatch:manifest_vs_artifacts")

        # Per-paper source_chunk_id set alignment across stages.
        bad_stage_alignment = []
        for pid in sorted(paper_ids):
            if raw_by_paper.get(pid, set()) != rule_by_paper.get(pid, set()) or raw_by_paper.get(pid, set()) != llm_by_paper.get(pid, set()):
                bad_stage_alignment.append(pid)
        if bad_stage_alignment:
            errors.append("raw_rule_llm_source_set_mismatch")

        # Global uniqueness check (the fixed logic from step4).
        source_sets = list(raw_by_paper.values())
        all_ids: Set[str] = set()
        total_expected = sum(len(s) for s in source_sets)
        for s in source_sets:
            all_ids |= s
        global_unique = len(all_ids) == total_expected
        if not global_unique:
            errors.append("global_source_chunk_id_misaligned")

        report["id_alignment"] = {
            "raw_rule_llm_per_paper_aligned": not bool(bad_stage_alignment),
            "bad_stage_alignment_papers": bad_stage_alignment[:20],
            "global_source_chunk_id_unique": global_unique,
            "global_raw_source_chunk_id_total_expected": total_expected,
            "global_raw_source_chunk_id_unique": len(all_ids),
        }

        evidence = _evidence_distribution(raw_all)
        report["evidence_distribution"] = evidence

        connections.connect(alias="v25_corpus", host=args.milvus_host, port=args.milvus_port)
        stage_reports: Dict[str, Dict[str, Any]] = {}
        for stage in ["raw", "rule", "llm"]:
            name = stage_collection_name(stage, args.collection_suffix)
            stat = _collection_stats("v25_corpus", name)
            stage_reports[stage] = stat

            if not stat["exists"]:
                errors.append(f"collection_missing:{name}")
                continue
            if int(stat["entity_count"]) != 1222:
                errors.append(f"collection_entity_count_mismatch:{stage}:{stat['entity_count']}!=1222")
            if len(stat["paper_ids"]) != 50:
                errors.append(f"collection_paper_count_mismatch:{stage}:{len(stat['paper_ids'])}!=50")
            if manifest_ids and stat["paper_ids"] != manifest_ids:
                errors.append(f"collection_paper_ids_mismatch:{stage}")

            raw_ids = set(raw_by_paper.keys())
            if manifest_ids and raw_ids != manifest_ids:
                errors.append("artifact_paper_ids_mismatch_manifest")

            raw_source_union = set().union(*raw_by_paper.values()) if raw_by_paper else set()
            if stage == "raw" and stat["source_chunk_ids"] != raw_source_union:
                errors.append("raw_collection_source_chunk_ids_mismatch_artifacts")
            if stage in {"rule", "llm"} and stat["source_chunk_ids"] != raw_source_union:
                errors.append(f"{stage}_collection_source_chunk_ids_mismatch_artifacts")

        report["stage_counts"] = {
            stage: {
                "collection": stat["name"],
                "exists": stat["exists"],
                "entity_count": stat["entity_count"],
                "paper_count": len(stat["paper_ids"]),
                "source_chunk_id_count": len(stat["source_chunk_ids"]),
            }
            for stage, stat in stage_reports.items()
        }

        # Coverage capability for v2.5 family requirements.
        table_capable = evidence["table_like_chunks"] > 0
        figure_capable = evidence["figure_like_chunks"] > 0
        numeric_capable = evidence["numeric_like_chunks"] > 0
        coverage_status = "PASS"
        if not table_capable or not figure_capable:
            coverage_status = "COVERAGE_BLOCKED"

        report["coverage_capability"] = {
            "table_capable": table_capable,
            "figure_capable": figure_capable,
            "numeric_capable": numeric_capable,
            "status": coverage_status,
            "notes": (
                "table/figure evidence missing in current raw chunk artifacts"
                if coverage_status != "PASS"
                else "all required evidence types available"
            ),
        }

        report["checks"] = [{"name": "hard_consistency", "status": "PASS" if not errors else "BLOCKED", "errors": errors}]
        report["status"] = "PASS" if not errors else "BLOCKED"

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        errors.append(str(exc))

    json_path = out_dir / "corpus_consistency_report.json"
    md_path = out_dir / "corpus_consistency_report.md"
    write_json(json_path, report)

    lines = [
        f"- status: {report.get('status')}",
        f"- manifest: {report.get('manifest_path')}",
        f"- artifact_root: {report.get('artifact_root')}",
        "",
        "## Paper Counts",
        f"- manifest: {report.get('paper_count', {}).get('manifest', 0)}",
        f"- parse_artifacts: {report.get('paper_count', {}).get('parse_artifacts', 0)}",
        f"- chunks_raw: {report.get('paper_count', {}).get('chunk_artifacts_raw', 0)}",
        f"- chunks_rule: {report.get('paper_count', {}).get('chunk_artifacts_rule', 0)}",
        f"- chunks_llm: {report.get('paper_count', {}).get('chunk_artifacts_llm', 0)}",
        "",
        "## Collections",
    ]
    for stage, stat in report.get("stage_counts", {}).items():
        lines.append(
            f"- {stage}: exists={stat.get('exists')} entity_count={stat.get('entity_count')} paper_count={stat.get('paper_count')} source_chunk_id_count={stat.get('source_chunk_id_count')}"
        )

    cov = report.get("coverage_capability", {})
    lines.extend(
        [
            "",
            "## Coverage Capability",
            f"- status: {cov.get('status')}",
            f"- table_capable: {cov.get('table_capable')}",
            f"- figure_capable: {cov.get('figure_capable')}",
            f"- numeric_capable: {cov.get('numeric_capable')}",
            f"- notes: {cov.get('notes')}",
        ]
    )

    errs = errors if errors else ["none"]
    lines.extend(["", "## Errors"] + [f"- {e}" for e in errs])
    write_markdown(md_path, "v2.5 Corpus Consistency Report", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
