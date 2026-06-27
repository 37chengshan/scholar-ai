from __future__ import annotations

from pathlib import Path

from app.models.paper import Paper


def test_paper_search_ready_orm_column_uses_canonical_name() -> None:
    column = Paper.is_search_ready.property.columns[0]

    assert column.name == "isSearchReady"
    assert "isSearchReady" in Paper.__table__.columns.keys()


def test_review_tables_have_formal_alembic_migration() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "015_add_review_tables_and_align_paper_indexes.py"
    )
    content = migration_path.read_text(encoding="utf-8")

    assert migration_path.exists()
    assert 'op.create_table(\n            "review_drafts"' in content
    assert 'op.create_table(\n            "review_runs"' in content
    assert 'op.create_index("idx_review_drafts_kb_user"' in content
    assert 'op.create_index("idx_review_runs_kb_user"' in content
