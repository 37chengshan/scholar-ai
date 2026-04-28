from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]


def build_citation_jump_url(
    paper_id: str,
    source_chunk_id: str,
    page_num: int | None = None,
    source: str = "evidence",
) -> str:
    page = page_num or 1
    return f"/read/{paper_id}?page={page}&source={source}&source_id={source_chunk_id}"


@lru_cache(maxsize=1)
def load_chunk_index() -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    papers_root = ROOT / "artifacts" / "papers"
    if not papers_root.exists():
        return idx

    for paper_dir in papers_root.iterdir():
        if not paper_dir.is_dir():
            continue

        for stage in ("raw", "rule", "llm"):
            fp = paper_dir / f"chunks_{stage}.json"
            if not fp.exists():
                continue

            data = json.loads(fp.read_text(encoding="utf-8"))
            chunks = data.get("chunks", []) if isinstance(data, dict) else []
            for chunk in chunks:
                source_id = str(chunk.get("source_chunk_id") or "")
                if not source_id:
                    continue

                paper_id = str(chunk.get("paper_id") or paper_dir.name)
                page_num = chunk.get("page_num")
                section_path = (
                    chunk.get("normalized_section_path")
                    or chunk.get("section_path")
                    or ""
                )
                content = str(chunk.get("text") or chunk.get("content") or "")
                anchor_text = str(chunk.get("anchor_text") or content)[:300]
                content_type = str(chunk.get("content_type") or "text")
                citation_jump_url = build_citation_jump_url(
                    paper_id=paper_id,
                    source_chunk_id=source_id,
                    page_num=page_num if isinstance(page_num, int) else None,
                )

                idx[source_id] = {
                    "evidence_id": source_id,
                    "source_type": "paper",
                    "source_chunk_id": source_id,
                    "paper_id": paper_id,
                    "page_num": page_num,
                    "section_path": section_path,
                    "content_type": content_type,
                    "anchor_text": anchor_text,
                    "content": content,
                    "pdf_url": f"/api/v1/papers/{paper_id}/pdf",
                    "citation_jump_url": citation_jump_url,
                    "read_url": citation_jump_url,
                }

    return idx


def get_evidence_source_payload(source_chunk_id: str) -> dict[str, Any] | None:
    return load_chunk_index().get(source_chunk_id)
