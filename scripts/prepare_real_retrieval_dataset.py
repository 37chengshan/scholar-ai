#!/usr/bin/env python
"""Prepare a small real-PDF retrieval dataset in paper_contents_v2."""

from __future__ import annotations

import argparse
import json
import re
import sys
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

DATASET_SPEC = [
    {
        "paper_id": "dataset-s-001",
        "source": "tests/evals/fixtures/papers/2303.08774.pdf",
        "title": "GPT-4 Technical Report",
        "queries": [
            {
                "id": "ds1-q1",
                "query": "What does the GPT-4 technical report say about multimodal capabilities?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-001"],
                "query_type": "single",
            },
            {
                "id": "ds1-q2",
                "query": "How is GPT-4 evaluated in the technical report?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-001"],
                "query_type": "single",
            },
        ],
    },
    {
        "paper_id": "dataset-s-002",
        "source": "tests/evals/fixtures/papers/2304.07193.pdf",
        "title": "DINOv2",
        "queries": [
            {
                "id": "ds2-q1",
                "query": "What problem does DINOv2 solve for visual representation learning?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-002"],
                "query_type": "single",
            },
            {
                "id": "ds2-q2",
                "query": "How does DINOv2 learn robust visual features?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-002"],
                "query_type": "single",
            },
        ],
    },
    {
        "paper_id": "dataset-s-003",
        "source": "tests/evals/fixtures/papers/2304.12244.pdf",
        "title": "WizardLM",
        "queries": [
            {
                "id": "ds3-q1",
                "query": "What is WizardLM designed to improve for large language models?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-003"],
                "query_type": "single",
            },
            {
                "id": "ds3-q2",
                "query": "How does WizardLM help models follow complex instructions?",
                "expected_sections": ["Abstract", "Introduction"],
                "expected_paper_ids": ["dataset-s-003"],
                "query_type": "single",
            },
        ],
    },
]

CROSS_PAPER_QUERIES = [
    {
        "id": "ds-cp1",
        "query": "Which paper focuses on multimodal large models and which one focuses on visual representation learning?",
        "paper_ids": ["dataset-s-001", "dataset-s-002"],
        "expected_paper_ids": ["dataset-s-001", "dataset-s-002"],
        "expected_sections": ["Abstract", "Introduction"],
        "query_type": "compare",
    },
    {
        "id": "ds-cp2",
        "query": "Which paper is about instruction following or model alignment?",
        "paper_ids": ["dataset-s-001", "dataset-s-003"],
        "expected_paper_ids": ["dataset-s-001", "dataset-s-003"],
        "expected_sections": ["Abstract", "Introduction"],
        "query_type": "compare",
    },
]

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


def normalize_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
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


def build_dataset_entries(spec: dict[str, Any], user_id: str, pages_per_paper: int) -> list[dict[str, Any]]:
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
                        "dataset": "dataset-s",
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


def build_golden_queries() -> dict[str, Any]:
    return {
        "version": "dataset-s-1.0",
        "papers": [
            {
                "paper_id": spec["paper_id"],
                "title": spec["title"],
                "queries": spec["queries"],
            }
            for spec in DATASET_SPEC
        ],
        "multimodal_queries": [],
        "cross_paper_queries": CROSS_PAPER_QUERIES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare real retrieval dataset")
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument("--pages-per-paper", type=int, default=4)
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "artifacts" / "benchmarks" / "real"),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    embedding_service = get_embedding_service()
    embedding_service.load_model()
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        qdrant = get_qdrant_service()
        qdrant.ensure_collection(vector_size=settings.EMBEDDING_DIMENSION)
    else:
        milvus = get_milvus_service()
        milvus.connect()
        milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    paper_ids = [spec["paper_id"] for spec in DATASET_SPEC]
    delete_existing_records(paper_ids, args.user_id)

    manifest_papers: list[dict[str, Any]] = []
    for spec in DATASET_SPEC:
        entries = build_dataset_entries(spec, args.user_id, args.pages_per_paper)
        if not entries:
            continue

        embeddings = embedding_service.encode_text([entry["text"] for entry in entries])
        for entry, embedding in zip(entries, embeddings):
            entry["embedding"] = embedding

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
        "dataset": "dataset-s",
        "backend": settings.VECTOR_STORE_BACKEND,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "papers": manifest_papers,
    }
    manifest_path = output_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    golden_queries = build_golden_queries()
    golden_path = output_dir / "golden_queries_dataset_s.json"
    golden_path.write_text(json.dumps(golden_queries, indent=2), encoding="utf-8")

    print(json.dumps({"manifest": str(manifest_path), "golden": str(golden_path), "papers": manifest_papers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
