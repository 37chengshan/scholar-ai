from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def iter_artifact_chunks(artifact_root: Path, stage: str) -> list[dict[str, Any]]:
    """Load flattened chunk rows from artifacts/papers/*/chunks_{stage}.json.

    This keeps Phase 2/3 builders deterministic and independent of runtime services.
    """
    rows: list[dict[str, Any]] = []
    if not artifact_root.exists():
        return rows

    for paper_dir in sorted(artifact_root.iterdir()):
        if not paper_dir.is_dir():
            continue
        paper_id = paper_dir.name
        chunk_file = paper_dir / f"chunks_{stage}.json"
        if not chunk_file.exists():
            chunk_file = paper_dir / "chunks_raw.json"
        if not chunk_file.exists():
            continue

        try:
            data = json.loads(chunk_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["paper_id"] = str(row.get("paper_id") or paper_id)
            row["source_chunk_id"] = str(row.get("source_chunk_id") or "")
            row["normalized_section_path"] = str(
                row.get("normalized_section_path")
                or row.get("section_path")
                or ""
            )
            row["content_type"] = str(row.get("content_type") or "text")
            rows.append(row)
    return rows
