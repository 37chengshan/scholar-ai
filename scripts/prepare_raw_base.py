#!/usr/bin/env python
"""Prepare raw base artifacts for v2/v2.1 (parse once, reuse everywhere)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from hashlib import md5
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent

DATASET_PROFILE_TO_COUNT = {
    "large-baseline": 12,
    "v2": 20,
    "v2.1": 20,
    "xlarge-main": 50,
}

SECTION_PATTERNS = [
    ("Abstract", re.compile(r"\babstract\b", re.IGNORECASE)),
    ("Introduction", re.compile(r"\bintroduction\b", re.IGNORECASE)),
    ("Related Work", re.compile(r"\brelated work\b", re.IGNORECASE)),
    ("Methods", re.compile(r"\b(method|methods|methodology)\b", re.IGNORECASE)),
    ("Experiments", re.compile(r"\b(experiments?|evaluation)\b", re.IGNORECASE)),
    ("Results", re.compile(r"\bresults?\b", re.IGNORECASE)),
    ("Discussion", re.compile(r"\bdiscussion\b", re.IGNORECASE)),
    ("Conclusion", re.compile(r"\bconclusion\b", re.IGNORECASE)),
]


def _list_pdf_files() -> list[Path]:
    paper_dir = ROOT / "tests" / "evals" / "fixtures" / "papers"
    return sorted(path for path in paper_dir.glob("*.pdf") if path.is_file())


def _to_title(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"v\d+$", "", stem)
    return stem.replace("_", " ")


def _paper_prefix(profile: str) -> str:
    if profile == "large-baseline":
        return "large"
    if profile in {"v2", "v2.1"}:
        return "v2"
    return "xlarge"


def _build_paper_specs(dataset_profile: str, paper_count: int) -> list[dict[str, Any]]:
    pdf_files = _list_pdf_files()
    if len(pdf_files) < paper_count:
        raise ValueError(f"Not enough fixture PDFs: required={paper_count}, found={len(pdf_files)}")

    selected = pdf_files[:paper_count]
    prefix = _paper_prefix(dataset_profile)
    specs: list[dict[str, Any]] = []
    for index, pdf_path in enumerate(selected, start=1):
        specs.append(
            {
                "paper_id": f"{prefix}-p-{index:03d}",
                "source_pdf": str(pdf_path.relative_to(ROOT)),
                "title": _to_title(pdf_path),
            }
        )
    return specs


def _remove_noisy_lines(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines()]
    cleaned: list[str] = []
    seen = Counter(lines)
    for line in lines:
        if not line:
            continue
        if len(line) < 3:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if "arxiv" in line.lower() and len(line) < 120:
            continue
        if seen[line] > 3 and len(line) < 80:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_text(text: str) -> str:
    no_noise = _remove_noisy_lines(text)
    return re.sub(r"\s+", " ", no_noise).strip()


def detect_section(text: str, page_number: int) -> str:
    sample = text[:2000]
    for section, pattern in SECTION_PATTERNS:
        if pattern.search(sample):
            return section
    if page_number <= 2:
        return "Introduction"
    return "Body"


def chunk_page_text(text: str, max_chars: int = 1400, overlap: int = 200) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + max_chars, text_length)
        chunks.append(text[start:end].strip())
        if end == text_length:
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def _raw_chunk_id(paper_id: str, page_num: int, chunk_index: int) -> str:
    key = f"{paper_id}:page_{page_num}:chunk_{chunk_index}"
    return md5(key.encode("utf-8")).hexdigest()[:16]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare raw base artifacts")
    parser.add_argument("--dataset-profile", choices=list(DATASET_PROFILE_TO_COUNT.keys()), default="v2")
    parser.add_argument("--paper-count", type=int, default=0)
    parser.add_argument("--pages-per-paper", type=int, default=4)
    parser.add_argument("--all-pages", action="store_true")
    parser.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    start_total = time.time()
    paper_count = args.paper_count or DATASET_PROFILE_TO_COUNT[args.dataset_profile]
    pages_per_paper = 0 if args.all_pages else args.pages_per_paper

    specs = _build_paper_specs(args.dataset_profile, paper_count)

    out_dir = Path(args.output_dir) / args.dataset_profile / "raw_base"
    out_dir.mkdir(parents=True, exist_ok=True)
    parsed_pages_jsonl = out_dir / "parsed_pages.jsonl"
    raw_chunks_jsonl = out_dir / "raw_chunks.jsonl"
    manifest_json = out_dir / "raw_chunks_manifest.json"
    paper_timing_jsonl = out_dir / "paper_stage_timing.jsonl"

    if not args.force and parsed_pages_jsonl.exists() and raw_chunks_jsonl.exists() and manifest_json.exists():
        print(f"[prepare-raw-base] reuse existing raw base: {out_dir}")
        return 0

    all_parsed_pages: list[dict[str, Any]] = []
    all_raw_chunks: list[dict[str, Any]] = []
    per_paper_timing: list[dict[str, Any]] = []

    parse_total = 0.0
    chunk_total = 0.0

    print(f"[prepare-raw-base] start extracting {len(specs)} papers")
    for idx, spec in enumerate(specs, start=1):
        paper_start = time.time()
        pdf_path = ROOT / spec["source_pdf"]
        reader = PdfReader(str(pdf_path))
        pages = list(reader.pages)
        selected_pages = pages if pages_per_paper <= 0 else pages[:pages_per_paper]

        print(f"[prepare-raw-base] ({idx}/{len(specs)}) {spec['paper_id']} parse")
        parse_start = time.time()
        page_rows: list[dict[str, Any]] = []
        for page_num, page in enumerate(selected_pages, start=1):
            raw_text = page.extract_text() or ""
            normalized = normalize_text(raw_text)
            if not normalized:
                continue
            section = detect_section(normalized, page_num)
            page_rows.append(
                {
                    "paper_id": spec["paper_id"],
                    "source_pdf": spec["source_pdf"],
                    "page_num": page_num,
                    "section_path": section,
                    "subsection": section,
                    "raw_text": normalized,
                    "parse_trace": {
                        "page_count": len(pages),
                        "pages_indexed": len(selected_pages),
                        "table_ref": [],
                        "figure_ref": [],
                        "caption_text": "",
                    },
                    "metadata": {
                        "title": spec["title"],
                    },
                }
            )
        parse_elapsed = time.time() - parse_start
        parse_total += parse_elapsed

        chunk_start = time.time()
        chunk_rows: list[dict[str, Any]] = []
        for page_row in page_rows:
            chunks = chunk_page_text(page_row["raw_text"])
            for c_idx, chunk_text in enumerate(chunks, start=1):
                raw_chunk_id = _raw_chunk_id(page_row["paper_id"], page_row["page_num"], c_idx)
                chunk_rows.append(
                    {
                        "raw_chunk_id": raw_chunk_id,
                        "source_chunk_id": raw_chunk_id,
                        "paper_id": page_row["paper_id"],
                        "source_pdf": page_row["source_pdf"],
                        "page_num": page_row["page_num"],
                        "section_path": page_row["section_path"],
                        "subsection": page_row["subsection"],
                        "raw_text": page_row["raw_text"],
                        "raw_chunk_text": chunk_text,
                        "metadata": {
                            "title": page_row["metadata"]["title"],
                            "chunk_index": c_idx,
                            "table_ref": page_row["parse_trace"].get("table_ref", []),
                            "figure_ref": page_row["parse_trace"].get("figure_ref", []),
                            "caption_text": page_row["parse_trace"].get("caption_text", ""),
                        },
                        "parse_trace": page_row["parse_trace"],
                    }
                )
        chunk_elapsed = time.time() - chunk_start
        chunk_total += chunk_elapsed

        all_parsed_pages.extend(page_rows)
        all_raw_chunks.extend(chunk_rows)

        paper_elapsed = time.time() - paper_start
        timing_row = {
            "paper_id": spec["paper_id"],
            "parse_pdf_seconds": round(parse_elapsed, 4),
            "chunk_raw_seconds": round(chunk_elapsed, 4),
            "build_rule_seconds": 0.0,
            "build_llm_seconds": 0.0,
            "embed_dense_seconds": 0.0,
            "build_sparse_seconds": 0.0,
            "insert_index_seconds": 0.0,
            "summary_index_seconds": round(paper_elapsed, 4),
            "chunk_count": len(chunk_rows),
        }
        per_paper_timing.append(timing_row)
        print(
            f"[prepare-raw-base] {spec['paper_id']} parsed_pages={len(page_rows)} "
            f"raw_chunks={len(chunk_rows)} parse={parse_elapsed:.2f}s chunk={chunk_elapsed:.2f}s"
        )

    _write_jsonl(parsed_pages_jsonl, all_parsed_pages)
    _write_jsonl(raw_chunks_jsonl, all_raw_chunks)
    _write_jsonl(paper_timing_jsonl, per_paper_timing)

    manifest = {
        "dataset_profile": args.dataset_profile,
        "paper_count": len(specs),
        "total_parsed_pages": len(all_parsed_pages),
        "total_chunks": len(all_raw_chunks),
        "pages_per_paper": pages_per_paper,
        "parse_pdf_seconds": round(parse_total, 4),
        "chunk_raw_seconds": round(chunk_total, 4),
        "summary_index_seconds": round(time.time() - start_total, 4),
        "artifacts": {
            "parsed_pages": str(parsed_pages_jsonl),
            "raw_chunks": str(raw_chunks_jsonl),
            "paper_timing": str(paper_timing_jsonl),
        },
        "papers": [
            {
                "paper_id": spec["paper_id"],
                "source_pdf": spec["source_pdf"],
                "title": spec["title"],
            }
            for spec in specs
        ],
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[prepare-raw-base] done papers={len(specs)} chunks={len(all_raw_chunks)}")
    print(f"[prepare-raw-base] parsed_pages={parsed_pages_jsonl}")
    print(f"[prepare-raw-base] raw_chunks={raw_chunks_jsonl}")
    print(f"[prepare-raw-base] manifest={manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
