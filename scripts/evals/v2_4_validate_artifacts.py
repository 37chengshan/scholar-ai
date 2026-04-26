#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from scripts.evals.v2_4_common import (
    DEFAULT_ARTIFACT_ROOT,
    DEFAULT_OUTPUT_DIR,
    REQUIRED_CHUNK_FIELDS,
    collect_paper_artifacts,
    content_type_valid,
    infer_ingest_status,
    read_json,
    required_field_missing,
    source_chunk_set,
    unique_source_chunk_ids,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 artifact consistency validator")
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--limit-papers", type=int, default=None)
    return p.parse_args()


def _safe_read(path: Path) -> Any:
    return read_json(path)


def main() -> int:
    args = parse_args()
    artifact_root = Path(args.artifact_root)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    errors: List[str] = []
    warnings: List[str] = []
    paper_reports: List[Dict[str, Any]] = []

    papers = collect_paper_artifacts(artifact_root, args.limit_papers)
    if not papers:
        errors.append(f"artifact_root_missing_or_empty:{artifact_root}")

    total_page_num = 0
    non_empty_page_num = 0

    for paper in papers:
        p_err: List[str] = []
        p_warn: List[str] = []

        if not paper.parse_artifact_path.exists():
            p_err.append("missing_parse_artifact")
        if not paper.chunks_raw_path.exists():
            p_err.append("missing_chunks_raw")
        if not paper.chunks_rule_path.exists():
            p_err.append("missing_chunks_rule")
        if not paper.chunks_llm_path.exists():
            p_err.append("missing_chunks_llm")

        raw_chunks: List[Dict[str, Any]] = []
        rule_chunks: List[Dict[str, Any]] = []
        llm_chunks: List[Dict[str, Any]] = []
        parse_artifact: Dict[str, Any] = {}

        if not p_err:
            parse_artifact = _safe_read(paper.parse_artifact_path)
            raw_chunks = list(_safe_read(paper.chunks_raw_path) or [])
            rule_chunks = list(_safe_read(paper.chunks_rule_path) or [])
            llm_chunks = list(_safe_read(paper.chunks_llm_path) or [])

            raw_set = source_chunk_set(raw_chunks)
            rule_set = source_chunk_set(rule_chunks)
            llm_set = source_chunk_set(llm_chunks)

            if raw_set != rule_set or raw_set != llm_set:
                p_err.append("source_chunk_id_alignment_failed")

            if not unique_source_chunk_ids(raw_chunks):
                p_err.append("raw_duplicate_source_chunk_id")
            if not unique_source_chunk_ids(rule_chunks):
                p_err.append("rule_duplicate_source_chunk_id")
            if not unique_source_chunk_ids(llm_chunks):
                p_err.append("llm_duplicate_source_chunk_id")

            for stage_name, chunks in (("raw", raw_chunks), ("rule", rule_chunks), ("llm", llm_chunks)):
                for chunk in chunks:
                    miss = required_field_missing(chunk, REQUIRED_CHUNK_FIELDS)
                    if miss:
                        p_err.append(f"{stage_name}_missing_fields:{','.join(sorted(set(miss)))}")
                        break
                    total_page_num += 1
                    if chunk.get("page_num") is not None:
                        non_empty_page_num += 1
                    if not content_type_valid(chunk.get("content_type")):
                        p_err.append(f"{stage_name}_invalid_content_type:{chunk.get('content_type')}")
                        break

            parse_mode = str(parse_artifact.get("parse_mode") or "")
            quality_level = str(parse_artifact.get("quality_level") or "")
            if parse_mode == "pypdf_fallback" and quality_level not in {"text_only", "degraded"}:
                p_err.append("pypdf_fallback_quality_not_text_only_or_degraded")

            # reject benchmark temporary parse payload mixed into official artifacts.
            paper_dir = paper.parse_artifact_path.parent
            if (paper_dir / "parsed_chunks.json").exists():
                p_err.append("benchmark_temporary_parse_payload_detected")

        if p_err:
            errors.extend([f"{paper.paper_id}:{e}" for e in p_err])
        if p_warn:
            warnings.extend([f"{paper.paper_id}:{w}" for w in p_warn])

        paper_reports.append(
            {
                "paper_id": paper.paper_id,
                "status": "PASS" if not p_err else "BLOCKED",
                "errors": p_err,
                "warnings": p_warn,
                "parse_artifact": str(paper.parse_artifact_path),
                "raw_chunks": str(paper.chunks_raw_path),
                "rule_chunks": str(paper.chunks_rule_path),
                "llm_chunks": str(paper.chunks_llm_path),
            }
        )

    page_num_ratio = (non_empty_page_num / total_page_num) if total_page_num else 0.0
    if total_page_num > 0 and page_num_ratio < 0.95:
        errors.append(f"page_num_non_empty_ratio_too_low:{page_num_ratio:.4f}")

    report: Dict[str, Any] = {
        "artifact_root": str(artifact_root),
        "papers_scanned": len(papers),
        "page_num_non_empty_ratio": round(page_num_ratio, 4),
        "errors": errors,
        "warnings": warnings,
        "paper_reports": paper_reports,
        "status": infer_ingest_status(errors),
    }

    write_json(out_dir / "artifact_consistency_report.json", report)

    lines = [
        f"- artifact_root: {report['artifact_root']}",
        f"- papers_scanned: {report['papers_scanned']}",
        f"- page_num_non_empty_ratio: {report['page_num_non_empty_ratio']}",
        f"- status: {report['status']}",
        "",
        "## Errors",
    ]
    lines.extend([f"- {e}" for e in errors] or ["- none"])
    lines.append("")
    lines.append("## Warnings")
    lines.extend([f"- {w}" for w in warnings] or ["- none"])
    write_markdown(out_dir / "artifact_consistency_report.md", "v2.4 Artifact Consistency Report", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
