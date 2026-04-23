#!/usr/bin/env python
"""Prepare benchmark retrieval datasets for 12-paper and 50-paper runs."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pypdf import PdfReader

from app.config import settings
from app.core.embedding.factory import get_embedding_service
from app.core.milvus_service import get_milvus_service
from app.core.qdrant_service import get_qdrant_service

DATASET_PROFILE_TO_COUNT = {
    "large-baseline": 12,
    "xlarge-main": 50,
}

QUERY_TARGET_BY_PROFILE = {
    "large-baseline": 48,
    "xlarge-main": 120,
}

QUERY_DISTRIBUTION = {
    "single_topic": 0.35,
    "single_section": 0.35,
    "cross_paper": 0.20,
    "hard": 0.10,
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


def detect_section(text: str, page_number: int) -> str:
    sample = text[:2000]
    for section, pattern in SECTION_PATTERNS:
        if pattern.search(sample):
            return section
    if page_number <= 2:
        return "Introduction"
    return "Body"


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
    compact = re.sub(r"\s+", " ", no_noise).strip()
    return compact


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


def _safe_entries_and_texts(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Build tokenizer-safe aligned entry/text lists."""
    safe_entries: list[dict[str, Any]] = []
    safe_texts: list[str] = []
    for entry in entries:
        text_value = entry.get("text", "")
        if text_value is None:
            continue
        if isinstance(text_value, str):
            normalized = text_value.strip()
        else:
            normalized = str(text_value).strip()
        if normalized:
            safe_entries.append(entry)
            safe_texts.append(normalized)
    return safe_entries, safe_texts


def _list_pdf_files() -> list[Path]:
    paper_dir = ROOT / "tests" / "evals" / "fixtures" / "papers"
    return sorted(path for path in paper_dir.glob("*.pdf") if path.is_file())


def _to_title(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"v\d+$", "", stem)
    return stem.replace("_", " ")


def _build_paper_specs(dataset_profile: str, paper_count: int) -> list[dict[str, Any]]:
    pdf_files = _list_pdf_files()
    if len(pdf_files) < paper_count:
        raise ValueError(f"Not enough fixture PDFs: required={paper_count}, found={len(pdf_files)}")

    selected = pdf_files[:paper_count]
    prefix = "large" if dataset_profile == "large-baseline" else "xlarge"
    specs: list[dict[str, Any]] = []
    for index, pdf_path in enumerate(selected, start=1):
        specs.append(
            {
                "paper_id": f"{prefix}-p-{index:03d}",
                "source": str(pdf_path.relative_to(ROOT)),
                "title": _to_title(pdf_path),
            }
        )
    return specs


def _single_queries(paper_id: str, title: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{paper_id}-topic",
            "query": f"What is the core research goal of {title}?",
            "expected_sections": ["Abstract", "Introduction"],
            "expected_section_titles": ["Abstract", "Introduction"],
            "expected_paper_ids": [paper_id],
            "expected_chunk_ids": [],
            "query_type": "single_topic",
        },
        {
            "id": f"{paper_id}-section",
            "query": f"Which evidence or experimental section in {title} supports the main claim?",
            "expected_sections": ["Experiments", "Results"],
            "expected_section_titles": ["Experiments", "Results"],
            "expected_paper_ids": [paper_id],
            "expected_chunk_ids": [],
            "query_type": "single_section",
        },
    ]


def _build_cross_and_hard_queries(
    *,
    specs: list[dict[str, Any]],
    target_count: int,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    total_single = len(specs) * 2
    remaining = max(target_count - total_single, 0)
    cross_target = int(math.floor(remaining * QUERY_DISTRIBUTION["cross_paper"]))
    hard_target = max(remaining - cross_target, 0)

    cross_queries: list[dict[str, Any]] = []
    for idx in range(cross_target):
        chosen = rng.sample(specs, k=min(2, len(specs)))
        paper_ids = [paper["paper_id"] for paper in chosen]
        cross_queries.append(
            {
                "id": f"cross-{idx+1:03d}",
                "query": f"Compare the main method difference between {chosen[0]['title']} and {chosen[-1]['title']}.",
                "paper_ids": paper_ids,
                "expected_paper_ids": paper_ids,
                "expected_sections": ["Introduction", "Methods"],
                "expected_section_titles": ["Introduction", "Methods"],
                "expected_chunk_ids": [],
                "query_type": "cross_paper",
            }
        )

    hard_queries: list[dict[str, Any]] = []
    for idx in range(hard_target):
        chosen = rng.sample(specs, k=min(3, len(specs)))
        paper_ids = [paper["paper_id"] for paper in chosen]
        hard_queries.append(
            {
                "id": f"hard-{idx+1:03d}",
                "query": "Identify conflicting findings and their evidence sections across these papers.",
                "paper_ids": paper_ids,
                "expected_paper_ids": paper_ids,
                "expected_sections": ["Results", "Discussion"],
                "expected_section_titles": ["Results", "Discussion"],
                "expected_chunk_ids": [],
                "query_type": "hard",
            }
        )

    return cross_queries, hard_queries


def build_dataset_entries(
    spec: dict[str, Any],
    user_id: str,
    pages_per_paper: int,
    dataset_profile: str,
    model_stack: str,
) -> list[dict[str, Any]]:
    pdf_path = ROOT / spec["source"]
    reader = PdfReader(str(pdf_path))
    entries: list[dict[str, Any]] = []

    for page_index, page in enumerate(reader.pages[:pages_per_paper], start=1):
        text = normalize_text(page.extract_text() or "")
        if not text:
            continue

        section = detect_section(text, page_index)
        for chunk_index, chunk_text in enumerate(chunk_page_text(text), start=1):
            entries.append(
                {
                    "paper_id": spec["paper_id"],
                    "user_id": user_id,
                    "content_type": "text",
                    "page_num": page_index,
                    "section": section,
                    "text": chunk_text,
                    "content_data": chunk_text,
                    "raw_data": {
                        "source_pdf": spec["source"],
                        "chunk_index": chunk_index,
                        "dataset_profile": dataset_profile,
                        "model_stack": model_stack,
                    },
                }
            )

    return entries


def delete_existing_records(paper_ids: list[str], user_id: str) -> None:
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        qdrant = get_qdrant_service()
        qdrant.ensure_collection(vector_size=settings.EMBEDDING_DIMENSION)
        qdrant.delete_by_paper_ids(user_id=user_id, paper_ids=paper_ids)
        return

    milvus = get_milvus_service()
    collection = milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)
    for paper_id in paper_ids:
        collection.delete(f'paper_id == "{paper_id}"')
    collection.flush()


def build_golden_queries(
    specs: list[dict[str, Any]],
    *,
    dataset_profile: str,
    model_stack: str,
    query_target: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    papers_payload: list[dict[str, Any]] = []
    all_queries: list[dict[str, Any]] = []
    for spec in specs:
        paper_queries = _single_queries(spec["paper_id"], spec["title"])
        all_queries.extend(paper_queries)
        papers_payload.append(
            {
                "paper_id": spec["paper_id"],
                "title": spec["title"],
                "queries": paper_queries,
            }
        )

    cross_queries, hard_queries = _build_cross_and_hard_queries(
        specs=specs,
        target_count=query_target,
        rng=rng,
    )

    query_counter = Counter(
        query.get("query_type", "unknown")
        for query in (all_queries + cross_queries + hard_queries)
    )

    return {
        "version": f"{dataset_profile}-1.0",
        "dataset_profile": dataset_profile,
        "model_stack": model_stack,
        "papers": papers_payload,
        "multimodal_queries": [],
        "cross_paper_queries": cross_queries + hard_queries,
        "query_type_stats": dict(query_counter),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare real retrieval dataset")
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument(
        "--dataset-profile",
        choices=list(DATASET_PROFILE_TO_COUNT.keys()),
        default="large-baseline",
    )
    parser.add_argument(
        "--model-stack",
        choices=["bge_dual", "qwen_dual"],
        default="qwen_dual",
    )
    parser.add_argument("--paper-count", type=int, default=0)
    parser.add_argument("--query-count", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pages-per-paper", type=int, default=4)
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "artifacts" / "benchmarks"),
    )
    args = parser.parse_args()

    paper_count = args.paper_count or DATASET_PROFILE_TO_COUNT[args.dataset_profile]
    query_count = args.query_count or QUERY_TARGET_BY_PROFILE[args.dataset_profile]
    specs = _build_paper_specs(args.dataset_profile, paper_count)

    output_dir = Path(args.output_dir)
    profile_dir = output_dir / args.dataset_profile / args.model_stack
    profile_dir.mkdir(parents=True, exist_ok=True)

    embedding_service = get_embedding_service()
    embedding_service.load_model()
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        qdrant = get_qdrant_service()
        qdrant.ensure_collection(vector_size=settings.EMBEDDING_DIMENSION)
    else:
        milvus = get_milvus_service()
        milvus.connect()
        milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    paper_ids = [spec["paper_id"] for spec in specs]
    delete_existing_records(paper_ids, args.user_id)

    manifest_papers: list[dict[str, Any]] = []
    for spec in specs:
        entries = build_dataset_entries(
            spec,
            args.user_id,
            args.pages_per_paper,
            args.dataset_profile,
            args.model_stack,
        )
        if not entries:
            continue

        safe_entries, texts = _safe_entries_and_texts(entries)
        if not texts:
            continue
        embeddings = embedding_service.encode_text(texts)
        for entry, embedding in zip(safe_entries, embeddings):
            entry["embedding"] = embedding

        entries = [entry for entry in safe_entries if "embedding" in entry]
        if not entries:
            continue

        if settings.VECTOR_STORE_BACKEND == "qdrant":
            inserted_ids = qdrant.upsert_contents_batched(entries)
        else:
            inserted_ids = milvus.insert_contents_batched(entries)
        manifest_papers.append(
            {
                "paper_id": spec["paper_id"],
                "title": spec["title"],
                "source_pdf": spec["source"],
                "user_id": args.user_id,
                "pages_indexed": args.pages_per_paper,
                "chunk_count": len(entries),
                "inserted_count": len(inserted_ids),
            }
        )

    manifest = {
        "dataset_profile": args.dataset_profile,
        "model_stack": args.model_stack,
        "backend": settings.VECTOR_STORE_BACKEND,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "paper_count": len(specs),
        "query_count_target": query_count,
        "papers": manifest_papers,
    }
    manifest_path = profile_dir / f"dataset_manifest_{args.dataset_profile}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    golden_queries = build_golden_queries(
        specs,
        dataset_profile=args.dataset_profile,
        model_stack=args.model_stack,
        query_target=query_count,
        seed=args.seed,
    )
    golden_path = profile_dir / f"golden_queries_{args.dataset_profile}.json"
    golden_path.write_text(json.dumps(golden_queries, indent=2), encoding="utf-8")

    stats_path = profile_dir / f"query_type_stats_{args.dataset_profile}.json"
    stats_path.write_text(
        json.dumps(golden_queries.get("query_type_stats", {}), indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "golden": str(golden_path),
                "stats": str(stats_path),
                "papers": manifest_papers,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
