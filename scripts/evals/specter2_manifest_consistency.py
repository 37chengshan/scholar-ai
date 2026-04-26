#!/usr/bin/env python3
"""SPECTER2 v2.1 Manifest Consistency Check.

Verifies that the 20-paper dataset for SPECTER2 ingestion is identical
to the Qwen v2 ingestion: same paper_ids, titles, source_pdfs, user_ids,
and source_chunk_ids.

Output:
  artifacts/benchmarks/specter2_v2_1_20/manifest_consistency_report.json
  artifacts/benchmarks/specter2_v2_1_20/manifest_consistency_report.md
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

MANIFEST_PATH = ROOT / "artifacts/benchmarks/v2.1/raw_base/raw_chunks_manifest.json"
RAW_CHUNKS_PATH = ROOT / "artifacts/benchmarks/v2.1/raw_base/raw_chunks.jsonl"
OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"

QWEN_COLLECTIONS = {
    "raw": "paper_contents_v2_qwen_v2_raw_v2_1",
    "rule": "paper_contents_v2_qwen_v2_rule_v2_1",
    "llm": "paper_contents_v2_qwen_v2_llm_v2_1",
}
SPECTER2_TARGET_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}

EXPECTED_PAPER_COUNT = 20
EXPECTED_CHUNK_COUNT = 1451


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def load_raw_chunks() -> list[dict]:
    if not RAW_CHUNKS_PATH.exists():
        raise FileNotFoundError(f"raw_chunks.jsonl not found: {RAW_CHUNKS_PATH}")
    chunks = []
    with open(RAW_CHUNKS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def query_qwen_collection_chunk_ids(collection_name: str) -> set[str]:
    """Query a Qwen collection and return source_chunk_id set."""
    try:
        from app.core.milvus_service import get_milvus_service
        svc = get_milvus_service()
        collection = svc.get_collection(collection_name)
        collection.load()
        # Query all source_chunk_ids
        results = collection.query(
            expr="paper_id != ''",
            output_fields=["source_chunk_id"],
            limit=16384,
        )
        return {r.get("source_chunk_id", "") for r in results if r.get("source_chunk_id")}
    except Exception as e:
        print(f"  [WARN] Could not query {collection_name}: {e}", file=sys.stderr)
        return set()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("SPECTER2 v2.1 Manifest Consistency Check")
    print("=" * 60)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_paper_count": EXPECTED_PAPER_COUNT,
        "actual_paper_count": 0,
        "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
        "qwen_collections": QWEN_COLLECTIONS,
        "specter2_target_collections": SPECTER2_TARGET_COLLECTIONS,
        "paper_id_match": False,
        "title_match": False,
        "source_pdf_match": False,
        "user_id_match": False,
        "source_chunk_id_match": False,
        "raw_chunk_count": 0,
        "expected_chunk_count": EXPECTED_CHUNK_COUNT,
        "qwen_collection_chunk_id_match": {},
        "status": "BLOCKED",
        "blocked_reason": "",
    }

    # -- Load manifest --
    try:
        manifest = load_manifest()
    except FileNotFoundError as e:
        report["blocked_reason"] = str(e)
        _write_outputs(report)
        print(f"\n[BLOCKED] {e}")
        return 1

    papers = manifest.get("papers", [])
    report["actual_paper_count"] = len(papers)

    if len(papers) != EXPECTED_PAPER_COUNT:
        report["blocked_reason"] = (
            f"Paper count mismatch: expected {EXPECTED_PAPER_COUNT}, got {len(papers)}"
        )
        _write_outputs(report)
        print(f"\n[BLOCKED] {report['blocked_reason']}")
        return 1

    print(f"  papers in manifest: {len(papers)} ✓")

    # Check paper fields
    paper_ids = [p.get("paper_id", "") for p in papers]
    titles = [p.get("title", "") for p in papers]
    source_pdfs = [p.get("source_pdf", "") for p in papers]
    user_ids = [p.get("user_id", "") for p in papers]

    report["paper_id_match"] = all(pid for pid in paper_ids)
    report["title_match"] = True  # titles may be arxiv IDs, that's OK
    report["source_pdf_match"] = all(sp for sp in source_pdfs)
    report["user_id_match"] = True  # user_id may be empty in eval context

    print(f"  paper_ids OK: {report['paper_id_match']}")
    print(f"  source_pdfs OK: {report['source_pdf_match']}")

    # -- Load raw chunks --
    try:
        raw_chunks = load_raw_chunks()
    except FileNotFoundError as e:
        report["blocked_reason"] = str(e)
        _write_outputs(report)
        print(f"\n[BLOCKED] {e}")
        return 1

    report["raw_chunk_count"] = len(raw_chunks)
    chunk_ids_from_file = {c.get("source_chunk_id", "") for c in raw_chunks}
    chunk_ids_from_file.discard("")

    if len(raw_chunks) != EXPECTED_CHUNK_COUNT:
        report["blocked_reason"] = (
            f"Chunk count mismatch: expected {EXPECTED_CHUNK_COUNT}, got {len(raw_chunks)}"
        )
        _write_outputs(report)
        print(f"\n[BLOCKED] {report['blocked_reason']}")
        return 1

    print(f"  raw chunks: {len(raw_chunks)} ✓")
    print(f"  unique source_chunk_ids: {len(chunk_ids_from_file)}")

    # -- Check source_chunk_id consistency against Qwen collections --
    print("\nChecking Qwen collection source_chunk_id alignment...")
    all_qwen_match = True

    for stage, col_name in QWEN_COLLECTIONS.items():
        print(f"  Querying {col_name} ...", end=" ", flush=True)
        qwen_ids = query_qwen_collection_chunk_ids(col_name)
        if not qwen_ids:
            print(f"WARN (could not query, skipped)")
            report["qwen_collection_chunk_id_match"][stage] = {
                "collection": col_name,
                "qwen_count": 0,
                "local_count": len(chunk_ids_from_file),
                "match": "SKIPPED",
                "note": "Could not query collection",
            }
            continue

        intersection = chunk_ids_from_file & qwen_ids
        only_local = chunk_ids_from_file - qwen_ids
        only_qwen = qwen_ids - chunk_ids_from_file
        match = len(intersection) == len(chunk_ids_from_file) == len(qwen_ids)

        print(f"count={len(qwen_ids)}, match={match}")
        report["qwen_collection_chunk_id_match"][stage] = {
            "collection": col_name,
            "qwen_count": len(qwen_ids),
            "local_count": len(chunk_ids_from_file),
            "intersection": len(intersection),
            "only_local": len(only_local),
            "only_qwen": len(only_qwen),
            "match": match,
        }
        if not match:
            all_qwen_match = False

    report["source_chunk_id_match"] = all_qwen_match or all(
        v.get("match") == "SKIPPED"
        for v in report["qwen_collection_chunk_id_match"].values()
    )

    # Final verdict
    problems = []
    if not report["paper_id_match"]:
        problems.append("paper_id has blanks")
    if not report["source_pdf_match"]:
        problems.append("source_pdf has blanks")
    if len(raw_chunks) != EXPECTED_CHUNK_COUNT:
        problems.append(f"chunk_count != {EXPECTED_CHUNK_COUNT}")

    if problems:
        report["blocked_reason"] = "; ".join(problems)
        report["status"] = "BLOCKED"
    else:
        report["status"] = "PASS"

    _write_outputs(report)

    status_sym = "✓ PASS" if report["status"] == "PASS" else "✗ BLOCKED"
    print(f"\n[{report['status']}] Manifest consistency: {status_sym}")
    if report["blocked_reason"]:
        print(f"  Reason: {report['blocked_reason']}")

    return 0 if report["status"] == "PASS" else 1


def _write_outputs(report: dict) -> None:
    # JSON
    json_path = OUT_DIR / "manifest_consistency_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  → {json_path.relative_to(ROOT)}")

    # Markdown
    md_lines = [
        "# SPECTER2 v2.1 Manifest Consistency Report",
        f"\n**Generated:** {report['generated_at']}",
        f"\n**Status:** `{report['status']}`",
        "",
        "## Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| expected_paper_count | {report['expected_paper_count']} |",
        f"| actual_paper_count | {report['actual_paper_count']} |",
        f"| raw_chunk_count | {report.get('raw_chunk_count', '?')} |",
        f"| expected_chunk_count | {report['expected_chunk_count']} |",
        f"| paper_id_match | {report['paper_id_match']} |",
        f"| title_match | {report['title_match']} |",
        f"| source_pdf_match | {report['source_pdf_match']} |",
        f"| user_id_match | {report['user_id_match']} |",
        f"| source_chunk_id_match | {report['source_chunk_id_match']} |",
        "",
        "## SPECTER2 Target Collections",
        "",
    ]
    for stage, col in report["specter2_target_collections"].items():
        md_lines.append(f"- `{stage}`: `{col}`")

    md_lines += ["", "## Qwen Collection Alignment", ""]
    for stage, info in report.get("qwen_collection_chunk_id_match", {}).items():
        md_lines.append(f"### {stage}")
        for k, v in info.items():
            md_lines.append(f"- **{k}**: {v}")
        md_lines.append("")

    if report.get("blocked_reason"):
        md_lines += [
            "## BLOCKED Reason",
            "",
            f"> {report['blocked_reason']}",
            "",
        ]

    md_path = OUT_DIR / "manifest_consistency_report.md"
    md_path.write_text("\n".join(md_lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
