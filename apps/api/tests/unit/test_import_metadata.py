"""Regression tests for import-workflow ORM metadata registration."""

from app.models import Base


def test_import_workflow_tables_are_registered_in_metadata() -> None:
    """Import tables must exist in metadata for local schema bootstrap."""
    expected_tables = {
        "import_jobs",
        "import_batches",
        "knowledge_base_papers",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())
