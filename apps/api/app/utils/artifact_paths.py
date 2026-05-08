from __future__ import annotations

from pathlib import Path


def resolve_repo_root(start: str | Path) -> Path:
    current = Path(start).resolve()
    for parent in current.parents:
        if (parent / "apps").exists() and (parent / "docs").exists():
            return parent
    for parent in current.parents:
        if (parent / "app").exists():
            return parent
    return current.parents[min(2, len(current.parents) - 1)]


def resolve_artifact_papers_root(start: str | Path) -> Path:
    repo_root = resolve_repo_root(start)
    papers_root = repo_root / "artifacts" / "papers"
    if papers_root.exists():
        return papers_root
    return papers_root
