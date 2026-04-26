from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter()
ROOT = Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def _load_chunk_index() -> dict[str, dict[str, Any]]:
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
            for ch in chunks:
                source_id = str(ch.get("source_chunk_id") or "")
                if not source_id:
                    continue
                idx[source_id] = {
                    "source_chunk_id": source_id,
                    "paper_id": ch.get("paper_id") or paper_dir.name,
                    "page_num": ch.get("page_num"),
                    "section_path": ch.get("normalized_section_path") or ch.get("section_path") or "",
                    "content_type": ch.get("content_type") or "text",
                    "anchor_text": (ch.get("anchor_text") or ch.get("text") or "")[:300],
                    "content": ch.get("text") or ch.get("content") or "",
                    "pdf_url": f"/api/v1/papers/{ch.get('paper_id') or paper_dir.name}/pdf",
                }
    return idx


@router.get("/source/{source_chunk_id}")
async def get_evidence_source(source_chunk_id: str):
    idx = _load_chunk_index()
    item = idx.get(source_chunk_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source chunk not found",
        )

    return {
        **item,
        "read_url": f"/read/{item['paper_id']}?page={item.get('page_num') or 1}&source_id={source_chunk_id}",
    }
