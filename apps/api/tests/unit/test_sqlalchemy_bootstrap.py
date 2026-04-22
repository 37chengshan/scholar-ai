"""Tests for SQLAlchemy non-production schema bootstrap helpers."""

from unittest.mock import MagicMock

import app.models  # noqa: F401
from app.database import _create_tables_in_order, _resolve_table_creation_order, Base


def test_resolve_table_creation_order_includes_dependencies_before_requested_tables():
    ordered_names = _resolve_table_creation_order(
        ("knowledge_base_papers", "import_batches", "import_jobs")
    )

    for required_name in (
        "users",
        "knowledge_bases",
        "papers",
        "processing_tasks",
        "import_batches",
        "import_jobs",
        "knowledge_base_papers",
    ):
        assert required_name in ordered_names

    assert ordered_names.index("users") < ordered_names.index("knowledge_bases")
    assert ordered_names.index("knowledge_bases") < ordered_names.index("knowledge_base_papers")
    assert ordered_names.index("papers") < ordered_names.index("knowledge_base_papers")
    assert ordered_names.index("processing_tasks") < ordered_names.index("import_jobs")
    assert ordered_names.index("import_batches") < ordered_names.index("import_jobs")


def test_resolve_table_creation_order_includes_auth_dependencies_for_e2e_bootstrap():
    ordered_names = _resolve_table_creation_order(
        (
            "roles",
            "users",
            "user_roles",
            "refresh_tokens",
            "knowledge_base_papers",
            "import_batches",
            "import_jobs",
        )
    )

    for required_name in (
        "roles",
        "users",
        "user_roles",
        "refresh_tokens",
        "knowledge_bases",
        "papers",
        "knowledge_base_papers",
        "processing_tasks",
        "import_batches",
        "import_jobs",
    ):
        assert required_name in ordered_names

    assert ordered_names.index("users") < ordered_names.index("user_roles")
    assert ordered_names.index("roles") < ordered_names.index("user_roles")
    assert ordered_names.index("users") < ordered_names.index("refresh_tokens")


def test_create_tables_in_order_uses_checkfirst_for_each_table(monkeypatch):
    ordered_names = ("users", "knowledge_bases", "papers")
    created_tables: list[tuple[str, bool]] = []
    sync_conn = MagicMock()

    table_by_name = {table.name: table for table in Base.metadata.sorted_tables}
    for table_name in ordered_names:
        monkeypatch.setattr(
            table_by_name[table_name],
            "create",
            lambda connection, checkfirst, current=table_name: created_tables.append(
                (current, checkfirst)
            ),
        )

    _create_tables_in_order(sync_conn, ordered_names)

    assert created_tables == [("users", True), ("knowledge_bases", True), ("papers", True)]