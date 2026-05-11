from __future__ import annotations

import os
from pathlib import Path


def resolve_repo_root(start: str | Path) -> Path:
    override = os.getenv("SCHOLAR_AI_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    current = Path(start).resolve()
    for parent in current.parents:
        if parent.name == "app" and parent.parent.name == "api" and parent.parent.parent.name == "apps":
            return parent.parent.parent.parent
        if parent.name == "api" and parent.parent.name == "apps":
            return parent.parent.parent
        if parent.name == "app" and (parent / "main.py").exists():
            return parent.parent
        if (parent / "artifacts").exists():
            return parent
        if (parent / "apps").exists() and (parent / "docs").exists():
            return parent
    return current.parents[min(2, len(current.parents) - 1)]


def resolve_artifact_papers_root(start: str | Path) -> Path:
    repo_root = resolve_repo_root(start)
    papers_root = repo_root / "artifacts" / "papers"
    if papers_root.exists():
        return papers_root
    return papers_root
