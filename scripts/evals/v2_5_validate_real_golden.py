#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

from pymilvus import Collection, connections

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

DEFAULT_GOLDEN = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_5"

MIN_FAMILY = {
    "fact": 20,
    "method": 10,
    "table": 8,
    "figure": 8,
    "numeric": 8,
    "compare": 8,
    "cross_paper": 8,
    "hard": 8,
}

NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|kpc|km|dex|sigma|ms|hz|ghz|mhz)?\b", re.IGNORECASE)

REQUIRED_QUERY_KEYS = {
    "query_id",
    "query",
    "query_family",
    "expected_answer_mode",
    "expected_paper_ids",
    "expected_source_chunk_ids",
    "expected_content_types",
    "expected_sections",
    "evidence_anchors",
    "golden_source",
    "difficulty",
    "notes",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.5 validate real golden")
    p.add_argument("--golden", default=str(DEFAULT_GOLDEN))
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _load_chunk_maps(artifact_root: Path) -> Dict[str, Dict[str, Any]]:
    artifact_map: Dict[str, Dict[str, Any]] = {}
    paper_ids: Set[str] = set()
    all_source_ids: Set[str] = set()

    for art in collect_paper_artifacts(artifact_root):
        raw = read_json(art.chunks_raw_path) if art.chunks_raw_path.exists() else []
        rule = read_json(art.chunks_rule_path) if art.chunks_rule_path.exists() else []
        llm = read_json(art.chunks_llm_path) if art.chunks_llm_path.exists() else []
        paper_ids.add(art.paper_id)

        for row in (raw + rule + llm):
            sid = str(row.get("source_chunk_id") or "")
            if not sid:
                continue
            all_source_ids.add(sid)
            if sid not in artifact_map:
                artifact_map[sid] = {
                    "paper_id": str(row.get("paper_id") or ""),
                    "content_type": str(row.get("content_type") or ""),
                    "section": str(row.get("normalized_section_path") or row.get("section_path") or "body"),
                    "content_data": str(row.get("content_data") or ""),
                    "anchor_text": str(row.get("anchor_text") or ""),
                }

    return {
        "artifact_map": artifact_map,
        "paper_ids": paper_ids,
        "source_ids": all_source_ids,
    }


def _load_collection_ids(suffix: str, host: str, port: int) -> Dict[str, Set[str]]:
    connections.connect(alias="v25_validate", host=host, port=port)
    paper_ids: Set[str] = set()
    source_ids: Set[str] = set()
    stage_source_ids: Dict[str, Set[str]] = {}

    for stage in ["raw", "rule", "llm"]:
        name = stage_collection_name(stage, suffix)
        col = Collection(name, using="v25_validate")
        col.load()
        rows = col.query(expr="id >= 0", output_fields=["paper_id", "source_chunk_id"], limit=16384)
        stage_ids = {str(r.get("source_chunk_id") or "") for r in rows if str(r.get("source_chunk_id") or "")}
        stage_source_ids[stage] = stage_ids
        source_ids |= stage_ids
        paper_ids |= {str(r.get("paper_id") or "") for r in rows if str(r.get("paper_id") or "")}

    return {
        "paper_ids": paper_ids,
        "source_ids": source_ids,
        "stage_source_ids": stage_source_ids,
    }


def validate_query_schema(query: Dict[str, Any]) -> bool:
    missing = REQUIRED_QUERY_KEYS - set(query.keys())
    if missing:
        return False
    if not str(query.get("query_id") or "").strip():
        return False
    if not str(query.get("query") or "").strip():
        return False
    if not isinstance(query.get("expected_paper_ids"), list):
        return False
    if not isinstance(query.get("expected_source_chunk_ids"), list):
        return False
    if not isinstance(query.get("evidence_anchors"), list):
        return False
    return True


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    queries = payload.get("queries", []) if isinstance(payload, dict) else []

    corpus = _load_chunk_maps(Path(args.artifact_root))
    collections = _load_collection_ids(args.collection_suffix, args.milvus_host, args.milvus_port)

    errors: List[str] = []
    warnings: List[str] = []

    ids = [str(q.get("query_id") or "") for q in queries]
    duplicated_query_ids = sorted([x for x, c in Counter(ids).items() if x and c > 1])
    if duplicated_query_ids:
        errors.append(f"duplicated_query_id_count:{len(duplicated_query_ids)}")

    normalized_query_texts = [" ".join(str(q.get("query") or "").strip().lower().split()) for q in queries]
    duplicated_query_text_count = sum(c - 1 for c in Counter(normalized_query_texts).values() if c > 1)
    if duplicated_query_text_count > 0:
        errors.append(f"duplicated_query_text_count:{duplicated_query_text_count}")

    missing_paper_ids = 0
    missing_source_ids_artifact = 0
    missing_source_ids_collection = 0
    content_type_mismatch = 0
    cross_paper_invalid = 0
    table_invalid = 0
    figure_invalid = 0
    numeric_invalid = 0
    synthetic_paper_id_count = 0
    schema_invalid_count = 0

    families = Counter()

    for q in queries:
        if not validate_query_schema(q):
            schema_invalid_count += 1
            continue

        family = str(q.get("query_family") or "")
        families[family] += 1

        expected_paper_ids = [str(x) for x in (q.get("expected_paper_ids") or [])]
        expected_source_ids = [str(x) for x in (q.get("expected_source_chunk_ids") or [])]
        expected_content_types = set(str(x) for x in (q.get("expected_content_types") or []))

        for pid in expected_paper_ids:
            if pid.startswith("test-paper-"):
                synthetic_paper_id_count += 1
            if pid not in corpus["paper_ids"]:
                missing_paper_ids += 1

        for sid in expected_source_ids:
            if sid not in corpus["source_ids"]:
                missing_source_ids_artifact += 1
            if sid not in collections["source_ids"]:
                missing_source_ids_collection += 1
            if sid in corpus["artifact_map"]:
                actual_ctype = str(corpus["artifact_map"][sid].get("content_type") or "")
                if expected_content_types and actual_ctype not in expected_content_types:
                    content_type_mismatch += 1

        if family == "cross_paper" and len(set(expected_paper_ids)) < 2:
            cross_paper_invalid += 1

        if family == "table":
            ok = False
            for sid in expected_source_ids:
                row = corpus["artifact_map"].get(sid, {})
                ctype = str(row.get("content_type") or "")
                text = f"{row.get('content_data') or ''} {row.get('anchor_text') or ''}".lower()
                if ctype == "table" or "table" in text:
                    ok = True
                    break
            if not ok:
                table_invalid += 1

        if family == "figure":
            ok = False
            for sid in expected_source_ids:
                row = corpus["artifact_map"].get(sid, {})
                ctype = str(row.get("content_type") or "")
                text = f"{row.get('content_data') or ''} {row.get('anchor_text') or ''}".lower()
                if ctype in {"figure", "caption", "page"} or "figure" in text or "fig." in text:
                    ok = True
                    break
            if not ok:
                figure_invalid += 1

        if family == "numeric":
            ok = False
            if NUMERIC_PATTERN.search(str(q.get("query") or "")):
                ok = True
            if not ok:
                for sid in expected_source_ids:
                    row = corpus["artifact_map"].get(sid, {})
                    text = f"{row.get('content_data') or ''} {row.get('anchor_text') or ''}"
                    if NUMERIC_PATTERN.search(text):
                        ok = True
                        break
            if not ok:
                numeric_invalid += 1

    if synthetic_paper_id_count > 0:
        errors.append(f"synthetic_paper_id_count:{synthetic_paper_id_count}")
    if schema_invalid_count > 0:
        errors.append(f"query_schema_invalid_count:{schema_invalid_count}")
    if missing_paper_ids > 0:
        errors.append(f"missing_expected_paper_id_count:{missing_paper_ids}")
    if missing_source_ids_artifact > 0:
        errors.append(f"missing_expected_source_chunk_id_in_artifact:{missing_source_ids_artifact}")
    if missing_source_ids_collection > 0:
        errors.append(f"missing_expected_source_chunk_id_in_collection:{missing_source_ids_collection}")
    if content_type_mismatch > 0:
        errors.append(f"expected_content_type_mismatch_count:{content_type_mismatch}")
    if cross_paper_invalid > 0:
        errors.append(f"cross_paper_invalid_count:{cross_paper_invalid}")
    if table_invalid > 0:
        errors.append(f"table_query_invalid_count:{table_invalid}")
    if figure_invalid > 0:
        errors.append(f"figure_query_invalid_count:{figure_invalid}")
    if numeric_invalid > 0:
        errors.append(f"numeric_query_invalid_count:{numeric_invalid}")

    # Family coverage check with capability fallback.
    corpus_table_capable = any(v.get("content_type") == "table" or "table" in (v.get("content_data", "") + " " + v.get("anchor_text", "")).lower() for v in corpus["artifact_map"].values())
    corpus_figure_capable = any(v.get("content_type") in {"figure", "caption", "page"} or "figure" in (v.get("content_data", "") + " " + v.get("anchor_text", "")).lower() for v in corpus["artifact_map"].values())

    family_missing = {}
    for fam, minimum in MIN_FAMILY.items():
        have = int(families.get(fam, 0))
        if have < minimum:
            family_missing[fam] = {"have": have, "required": minimum}

    family_coverage_status = "PASS"
    if family_missing:
        blocked_by_capability = []
        hard_missing = []
        for fam in family_missing:
            if fam == "table" and not corpus_table_capable:
                blocked_by_capability.append(fam)
            elif fam == "figure" and not corpus_figure_capable:
                blocked_by_capability.append(fam)
            else:
                hard_missing.append(fam)

        if hard_missing:
            family_coverage_status = "BLOCKED"
            errors.append("family_coverage_missing:" + ",".join(sorted(hard_missing)))
        else:
            family_coverage_status = "CONDITIONAL"
            warnings.append("family_coverage_blocked_by_corpus_capability:" + ",".join(sorted(blocked_by_capability)))

    status = "PASS" if not errors and family_coverage_status == "PASS" else "BLOCKED"

    report = {
        "golden_path": str(Path(args.golden)),
        "query_count": len(queries),
        "queries_by_family": dict(families),
        "checks": {
            "query_id_unique": not bool(duplicated_query_ids),
            "expected_paper_id_exists": missing_paper_ids == 0,
            "expected_source_chunk_id_exists_in_artifact": missing_source_ids_artifact == 0,
            "expected_source_chunk_id_exists_in_collection": missing_source_ids_collection == 0,
            "expected_content_type_match": content_type_mismatch == 0,
            "cross_paper_valid": cross_paper_invalid == 0,
            "table_valid": table_invalid == 0,
            "figure_valid": figure_invalid == 0,
            "numeric_valid": numeric_invalid == 0,
            "synthetic_paper_id_count": synthetic_paper_id_count,
            "query_schema_invalid_count": schema_invalid_count,
            "missing_evidence_count": missing_source_ids_artifact + missing_source_ids_collection,
            "duplicated_query_count": duplicated_query_text_count,
        },
        "family_minimum_required": MIN_FAMILY,
        "family_missing": family_missing,
        "family_coverage_status": family_coverage_status,
        "errors": errors,
        "warnings": warnings,
        "status": status,
    }

    write_json(out_dir / "golden_consistency_50.json", report)
    lines = [
        f"- status: {status}",
        f"- query_count: {len(queries)}",
        f"- family_coverage_status: {family_coverage_status}",
        "",
        "## Family Counts",
    ]
    for fam in ["fact", "method", "table", "figure", "numeric", "compare", "cross_paper", "hard"]:
        lines.append(f"- {fam}: {families.get(fam, 0)} (required >= {MIN_FAMILY[fam]})")

    lines.extend(["", "## Errors"] + ([f"- {e}" for e in errors] if errors else ["- none"]))
    lines.extend(["", "## Warnings"] + ([f"- {w}" for w in warnings] if warnings else ["- none"]))
    write_markdown(out_dir / "golden_consistency_50.md", "v2.5 Golden Consistency (50 papers)", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
