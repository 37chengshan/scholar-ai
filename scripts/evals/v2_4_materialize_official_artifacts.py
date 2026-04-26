#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps" / "api"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.contracts.chunk_artifact import (  # noqa: E402
    ChunkArtifact,
    ChunkStage,
    build_chunk_artifacts,
    derive_stage_chunk_artifacts,
)
from app.contracts.parse_artifact import build_parse_artifact  # noqa: E402
from app.core.docling_service import DoclingParser  # noqa: E402
from app.core.imrad_extractor import extract_imrad_structure  # noqa: E402
from scripts.evals.v2_4_common import (  # noqa: E402
    DEFAULT_ARTIFACT_ROOT,
    source_chunk_set,
    write_json,
    write_markdown,
)


@dataclass(frozen=True)
class ManifestPaper:
    paper_id: str
    source_pdf: str
    title: str
    storage_key: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Official Artifact Materialization v1")
    p.add_argument("--manifest", default=None)
    p.add_argument("--paper-root", default=str(ROOT / "tests" / "evals" / "fixtures" / "papers"))
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--limit-papers", type=int, default=None)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dashboard-interval-seconds", type=int, default=10)
    p.add_argument("--user-id", default="benchmark-user")
    p.add_argument("--parse-backend", choices=["auto", "pypdf"], default="auto")
    return p.parse_args()


def _discover_manifest(explicit_manifest: Optional[str]) -> Path:
    if explicit_manifest:
        p = Path(explicit_manifest)
        if p.exists():
            return p
        raise FileNotFoundError(f"manifest_not_found:{p}")

    candidates = [
        ROOT / "artifacts" / "benchmarks" / "v2_4" / "manifest.json",
        ROOT / "artifacts" / "benchmarks" / "v2_3" / "manifest.json",
        ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "manifest.json",
        ROOT / "tests" / "evals" / "fixtures" / "papers" / "manifest.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("manifest_not_found_in_priority_paths")


def _load_manifest(path: Path, limit: Optional[int]) -> List[ManifestPaper]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    papers = payload.get("papers", []) if isinstance(payload, dict) else []

    output: List[ManifestPaper] = []
    for item in papers:
        paper_id = str(item.get("paper_id") or "").strip()
        source_pdf = str(item.get("source_pdf") or "").strip()
        title = str(item.get("title") or "").strip()
        if not paper_id or not source_pdf:
            continue
        output.append(
            ManifestPaper(
                paper_id=paper_id,
                source_pdf=source_pdf,
                title=title,
                storage_key=source_pdf,
            )
        )
        if limit is not None and len(output) >= limit:
            break
    return output


def _resolve_pdf_path(source_pdf: str, paper_root: Path) -> Path:
    src = Path(source_pdf)
    if src.is_absolute() and src.exists():
        return src

    direct = paper_root / source_pdf
    if direct.exists():
        return direct

    by_name = paper_root / src.name
    if by_name.exists():
        return by_name

    raise FileNotFoundError(f"source_pdf_missing:{source_pdf}")


def _paper_dir(artifact_root: Path, paper_id: str) -> Path:
    out = artifact_root / paper_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def _all_artifacts_exist(paper_dir: Path) -> bool:
    return all(
        (paper_dir / fn).exists()
        for fn in [
            "parse_artifact.json",
            "chunks_raw.json",
            "chunks_rule.json",
            "chunks_llm.json",
        ]
    )


def _extract_tables_figures_captions(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    tables: List[Dict[str, Any]] = []
    figures: List[Dict[str, Any]] = []
    captions: List[Dict[str, Any]] = []
    for item in items:
        t = str(item.get("type") or "").lower()
        if t == "table":
            tables.append(item)
        elif t in {"picture", "figure", "image"}:
            figures.append(item)
        elif t == "caption":
            captions.append(item)
    return tables, figures, captions


def _validate_source_chunk_alignment(raw: List[Dict[str, Any]], rule: List[Dict[str, Any]], llm: List[Dict[str, Any]]) -> None:
    rs = source_chunk_set(raw)
    us = source_chunk_set(rule)
    ls = source_chunk_set(llm)
    if rs != us or rs != ls:
        raise RuntimeError("source_chunk_id_alignment_failed")


def _clean_utf8(value: Any) -> Any:
    """Strip lone surrogates and other non-UTF-8 code points from strings."""
    if isinstance(value, str):
        import re
        return re.sub(r"[\ud800-\udfff]", "", value)
    if isinstance(value, list):
        return [_clean_utf8(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean_utf8(v) for k, v in value.items()}
    return value


def _to_chunk_payload(
    chunk: ChunkArtifact,
    *,
    user_id: str,
    stage: str,
) -> Dict[str, Any]:
    content_data = str(chunk.content_data or "")
    indexable = bool(content_data.strip())
    metadata: Dict[str, Any] = {"enrichment": stage}
    if not indexable:
        metadata["indexable_reason"] = "empty_content_data"

    return {
        "source_chunk_id": chunk.source_chunk_id,
        "chunk_id": chunk.chunk_id,
        "paper_id": chunk.paper_id,
        "user_id": user_id,
        "parse_id": chunk.parse_id,
        "page_num": int(chunk.page_num) if chunk.page_num is not None else 0,
        "section_path": str(chunk.section_path or "body"),
        "normalized_section_path": str(chunk.normalized_section_path or "body"),
        "content_type": chunk.content_type,
        "content_data": content_data,
        "anchor_text": str(chunk.anchor_text or ""),
        "char_start": int(chunk.char_start) if chunk.char_start is not None else 0,
        "char_end": int(chunk.char_end) if chunk.char_end is not None else 0,
        "stage": stage,
        "parent_source_chunk_id": chunk.parent_source_chunk_id,
        "indexable": indexable,
        "metadata": metadata,
    }


def _render_dashboard_markdown(path: Path, dashboard: Dict[str, Any]) -> None:
    lines = [
        f"Updated: {dashboard.get('updated')}",
        "",
        "## Manifest",
        f"- papers_expected: {dashboard['manifest']['papers_expected']}",
        f"- papers_loaded: {dashboard['manifest']['papers_loaded']}",
        f"- artifact_root: {dashboard['manifest']['artifact_root']}",
        "",
        "## Stages",
        f"- resolve_manifest: {dashboard['stages']['resolve_manifest']}",
        f"- materialize_parse_artifacts: {dashboard['stages']['materialize_parse_artifacts']}",
        f"- materialize_chunk_artifacts: {dashboard['stages']['materialize_chunk_artifacts']}",
        f"- validate_alignment: {dashboard['stages']['validate_alignment']}",
        "",
        "## Current",
        f"- paper_id: {dashboard['current'].get('paper_id', '')}",
        f"- source_pdf: {dashboard['current'].get('source_pdf', '')}",
        f"- parse_mode: {dashboard['current'].get('parse_mode', '')}",
        f"- raw_chunks: {dashboard['current'].get('raw_chunks', 0)}",
        f"- rule_chunks: {dashboard['current'].get('rule_chunks', 0)}",
        f"- llm_chunks: {dashboard['current'].get('llm_chunks', 0)}",
        f"- errors: {dashboard['current'].get('errors', 0)}",
        "",
        "## Progress",
        f"- parse_artifacts: {dashboard['progress']['parse_artifacts']}",
        f"- raw_chunks_files: {dashboard['progress']['raw_chunks_files']}",
        f"- rule_chunks_files: {dashboard['progress']['rule_chunks_files']}",
        f"- llm_chunks_files: {dashboard['progress']['llm_chunks_files']}",
        "",
        "## Recent Errors",
    ]
    recent = dashboard.get("recent_errors", [])
    lines.extend([f"- {e}" for e in recent] or ["- none"])
    write_markdown(path, "ScholarAI Official Artifact Materialization Dashboard", lines)


async def _materialize_one(
    *,
    parser: DoclingParser,
    paper: ManifestPaper,
    source_pdf_path: Path,
    artifact_root: Path,
    user_id: str,
    dry_run: bool,
    parse_backend: str,
) -> Dict[str, Any]:
    if dry_run:
        return {
            "paper_id": paper.paper_id,
            "source_pdf": str(source_pdf_path),
            "parse_mode": "PENDING",
            "quality_level": "PENDING",
            "raw_chunks": 0,
            "rule_chunks": 0,
            "llm_chunks": 0,
            "status": "PASS",
            "errors": [],
        }

    if parse_backend == "pypdf":
        parse_result = await parser._parse_pdf_with_pypdf(
            source_pdf_path,
            primary_error=RuntimeError("forced_pypdf_backend"),
        )
        if parse_result is None:
            raise RuntimeError("forced_pypdf_backend_failed")
    else:
        parse_result = await parser.parse_pdf(str(source_pdf_path))
    page_count = int(parse_result.get("page_count") or 0)
    if page_count <= 0:
        raise RuntimeError("invalid_page_count")

    parse_artifact = build_parse_artifact(
        paper_id=paper.paper_id,
        source_uri=paper.storage_key,
        parse_result=parse_result,
        parser_name="docling",
        parser_version=(parse_result.get("metadata") or {}).get("parser_version"),
    )
    parse_dump = parse_artifact.model_dump(mode="json")
    parse_dump.update(
        {
            "user_id": user_id,
            "storage_key": paper.storage_key,
            "source_pdf": str(source_pdf_path),
            "parser": "pypdf" if parse_dump.get("parse_mode") == "pypdf_fallback" else "docling",
        }
    )

    # Fill optional fields requested by report contract.
    items = list(_clean_utf8(parse_result.get("items") or []))
    tables, figures, captions = _extract_tables_figures_captions(items)
    parse_dump["pages"] = list(parse_result.get("pages") or [])
    parse_dump["tables"] = tables
    parse_dump["figures"] = figures
    parse_dump["captions"] = captions

    parse_mode = str(parse_dump.get("parse_mode") or "")
    quality_level = str(parse_dump.get("quality_level") or "")
    if parse_mode == "pypdf_fallback" and quality_level not in {"text_only", "degraded"}:
        parse_dump["quality_level"] = "text_only"
        quality_level = "text_only"

    imrad = extract_imrad_structure(items)
    semantic_chunks = parser.chunk_by_semantic(
        items,
        paper_id=paper.paper_id,
        imrad_structure=imrad,
    )

    raw_artifacts = build_chunk_artifacts(
        parse_id=str(parse_dump["parse_id"]),
        paper_id=paper.paper_id,
        semantic_chunks=semantic_chunks,
    )
    rule_artifacts = derive_stage_chunk_artifacts(raw_artifacts, ChunkStage.RULE)
    llm_artifacts = derive_stage_chunk_artifacts(raw_artifacts, ChunkStage.LLM)

    parse_dump = _clean_utf8(parse_dump)

    raw_payload = [_clean_utf8(_to_chunk_payload(chunk, user_id=user_id, stage="raw")) for chunk in raw_artifacts]
    rule_payload = [_clean_utf8(_to_chunk_payload(chunk, user_id=user_id, stage="rule")) for chunk in rule_artifacts]
    llm_payload = [_clean_utf8(_to_chunk_payload(chunk, user_id=user_id, stage="llm")) for chunk in llm_artifacts]

    _validate_source_chunk_alignment(raw_payload, rule_payload, llm_payload)

    for stage_name, payload in (("raw", raw_payload), ("rule", rule_payload), ("llm", llm_payload)):
        for row in payload:
            if not str(row.get("content_data") or "").strip():
                raise RuntimeError(f"empty_content_data:{stage_name}")
            if int(row.get("page_num") or 0) <= 0:
                raise RuntimeError(f"invalid_page_num:{stage_name}")

    paper_dir = _paper_dir(artifact_root, paper.paper_id)
    write_json(paper_dir / "parse_artifact.json", parse_dump)
    write_json(paper_dir / "chunks_raw.json", raw_payload)
    write_json(paper_dir / "chunks_rule.json", rule_payload)
    write_json(paper_dir / "chunks_llm.json", llm_payload)

    return {
        "paper_id": paper.paper_id,
        "source_pdf": str(source_pdf_path),
        "parse_mode": parse_mode,
        "quality_level": quality_level,
        "raw_chunks": len(raw_payload),
        "rule_chunks": len(rule_payload),
        "llm_chunks": len(llm_payload),
        "status": "PASS",
        "errors": [],
    }


async def _run() -> int:
    args = parse_args()

    out_dir = Path(args.artifact_root).resolve().parents[1] / "benchmarks" / "v2_4"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = Path(args.artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=True)

    manifest_path = _discover_manifest(args.manifest)
    papers = _load_manifest(manifest_path, args.limit_papers)

    dashboard: Dict[str, Any] = {
        "title": "ScholarAI Official Artifact Materialization Dashboard",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "manifest": {
            "papers_expected": len(papers),
            "papers_loaded": 0,
            "artifact_root": str(artifact_root),
            "manifest_path": str(manifest_path),
        },
        "stages": {
            "resolve_manifest": "DONE",
            "materialize_parse_artifacts": "PENDING",
            "materialize_chunk_artifacts": "PENDING",
            "validate_alignment": "PENDING",
        },
        "current": {
            "paper_id": "",
            "source_pdf": "",
            "parse_mode": "",
            "raw_chunks": 0,
            "rule_chunks": 0,
            "llm_chunks": 0,
            "errors": 0,
        },
        "progress": {
            "parse_artifacts": f"0/{len(papers)}",
            "raw_chunks_files": f"0/{len(papers)}",
            "rule_chunks_files": f"0/{len(papers)}",
            "llm_chunks_files": f"0/{len(papers)}",
        },
        "recent_errors": [],
    }

    parser = DoclingParser()
    # Materialization should not fail on long benchmark papers.
    parser.config.max_num_pages = max(int(parser.config.max_num_pages), 2000)
    last_flush = time.time()

    parse_success = 0
    raw_success = 0
    rule_success = 0
    llm_success = 0
    errors: List[str] = []
    paper_results: List[Dict[str, Any]] = []
    parse_mode_dist: Counter[str] = Counter()
    quality_dist: Counter[str] = Counter()

    dashboard["stages"]["materialize_parse_artifacts"] = "RUNNING"
    dashboard["stages"]["materialize_chunk_artifacts"] = "RUNNING"

    for paper in papers:
        dashboard["manifest"]["papers_loaded"] = dashboard["manifest"]["papers_loaded"] + 1

        try:
            source_pdf_path = _resolve_pdf_path(paper.source_pdf, Path(args.paper_root))
            paper_dir = _paper_dir(artifact_root, paper.paper_id)

            if args.resume and _all_artifacts_exist(paper_dir):
                result = {
                    "paper_id": paper.paper_id,
                    "source_pdf": str(source_pdf_path),
                    "parse_mode": "RESUME",
                    "quality_level": "RESUME",
                    "raw_chunks": 0,
                    "rule_chunks": 0,
                    "llm_chunks": 0,
                    "status": "PASS",
                    "errors": [],
                }
            else:
                if not args.force and not args.resume:
                    files_present = [
                        (paper_dir / "parse_artifact.json").exists(),
                        (paper_dir / "chunks_raw.json").exists(),
                        (paper_dir / "chunks_rule.json").exists(),
                        (paper_dir / "chunks_llm.json").exists(),
                    ]
                    if any(files_present) and not all(files_present):
                        raise RuntimeError("partial_artifacts_exist_use_force_or_resume")
                result = await _materialize_one(
                    parser=parser,
                    paper=paper,
                    source_pdf_path=source_pdf_path,
                    artifact_root=artifact_root,
                    user_id=args.user_id,
                    dry_run=args.dry_run,
                    parse_backend=args.parse_backend,
                )

            paper_results.append(result)
            if result["status"] == "PASS":
                parse_success += 1
                raw_success += 1
                rule_success += 1
                llm_success += 1
                parse_mode_dist[result["parse_mode"]] += 1
                quality_dist[result["quality_level"]] += 1
            else:
                errors.extend([f"{paper.paper_id}:{e}" for e in result.get("errors", [])])

            dashboard["current"] = {
                "paper_id": result["paper_id"],
                "source_pdf": result["source_pdf"],
                "parse_mode": result["parse_mode"],
                "raw_chunks": result["raw_chunks"],
                "rule_chunks": result["rule_chunks"],
                "llm_chunks": result["llm_chunks"],
                "errors": len(errors),
            }

        except Exception as exc:
            err = f"{paper.paper_id}:{exc}"
            errors.append(err)
            paper_results.append(
                {
                    "paper_id": paper.paper_id,
                    "source_pdf": paper.source_pdf,
                    "parse_mode": "ERROR",
                    "quality_level": "ERROR",
                    "raw_chunks": 0,
                    "rule_chunks": 0,
                    "llm_chunks": 0,
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                }
            )
            dashboard["recent_errors"] = (dashboard["recent_errors"] + [err])[-20:]
            dashboard["current"]["errors"] = len(errors)

        dashboard["progress"] = {
            "parse_artifacts": f"{parse_success}/{len(papers)}",
            "raw_chunks_files": f"{raw_success}/{len(papers)}",
            "rule_chunks_files": f"{rule_success}/{len(papers)}",
            "llm_chunks_files": f"{llm_success}/{len(papers)}",
        }
        dashboard["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        now = time.time()
        if now - last_flush >= args.dashboard_interval_seconds:
            write_json(out_dir / "artifact_materialization_dashboard.json", dashboard)
            _render_dashboard_markdown(out_dir / "artifact_materialization_dashboard.md", dashboard)
            last_flush = now

    dashboard["stages"]["materialize_parse_artifacts"] = "DONE" if parse_success == len(papers) else "BLOCKED"
    dashboard["stages"]["materialize_chunk_artifacts"] = "DONE" if raw_success == len(papers) else "BLOCKED"
    dashboard["stages"]["validate_alignment"] = "DONE" if not errors else "BLOCKED"
    dashboard["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report: Dict[str, Any] = {
        "manifest_path": str(manifest_path),
        "paper_count": len(papers),
        "artifact_root": str(artifact_root),
        "parse_artifact_success": parse_success,
        "chunks_raw_success": raw_success,
        "chunks_rule_success": rule_success,
        "chunks_llm_success": llm_success,
        "source_chunk_id_alignment": "PASS" if not errors else "BLOCKED",
        "parse_mode_distribution": dict(parse_mode_dist),
        "quality_level_distribution": dict(quality_dist),
        "errors": errors,
        "dry_run": bool(args.dry_run),
        "status": "PASS" if not errors else "BLOCKED",
        "papers": paper_results,
    }

    write_json(out_dir / "artifact_materialization_dashboard.json", dashboard)
    _render_dashboard_markdown(out_dir / "artifact_materialization_dashboard.md", dashboard)
    write_json(out_dir / "artifact_materialization_report.json", report)

    lines = [
        f"- manifest_path: {report['manifest_path']}",
        f"- paper_count: {report['paper_count']}",
        f"- artifact_root: {report['artifact_root']}",
        f"- parse_artifact_success: {report['parse_artifact_success']}",
        f"- chunks_raw_success: {report['chunks_raw_success']}",
        f"- chunks_rule_success: {report['chunks_rule_success']}",
        f"- chunks_llm_success: {report['chunks_llm_success']}",
        f"- source_chunk_id_alignment: {report['source_chunk_id_alignment']}",
        f"- status: {report['status']}",
        "",
        "## Parse Mode Distribution",
    ]
    lines.extend([f"- {k}: {v}" for k, v in sorted(report["parse_mode_distribution"].items())] or ["- none"])
    lines.extend(["", "## Quality Level Distribution"])
    lines.extend([f"- {k}: {v}" for k, v in sorted(report["quality_level_distribution"].items())] or ["- none"])
    lines.extend(["", "## Errors"])
    lines.extend([f"- {e}" for e in report["errors"]] or ["- none"])

    write_markdown(out_dir / "artifact_materialization_report.md", "Official Artifact Materialization v1", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
