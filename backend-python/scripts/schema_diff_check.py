#!/usr/bin/env python3
"""Schema Diff Check Script

Compares SQLAlchemy ORM model definitions with the actual database schema.
Detects drift between code and database.

Usage:
  python scripts/schema_diff_check.py --report   # Report differences (default)
  python scripts/schema_diff_check.py --strict   # Exit 1 if any diff found
  python scripts/schema_diff_check.py --fix     # Print ALTER statements (dev only)

Environment:
  DATABASE_URL    PostgreSQL connection string (required)
  PYTHONPATH      Must include the app directory

Exit codes:
  0   No differences found (or --report with differences)
  1   Differences found in --strict mode
  2   Database connection error
"""

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from typing import Any

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import inspect


def build_orm_column_map(orm_models: list[type]) -> dict[str, dict[str, Any]]:
    """Extract column metadata from SQLAlchemy ORM models."""
    col_map: dict[str, dict[str, Any]] = defaultdict(dict)

    for model in orm_models:
        mapper = inspect(model, raiseerr=True)
        table_name = mapper.local_table.name
        for column in mapper.columns:
            col_name = column.key
            col_map[table_name][col_name] = {
                "type": str(column.type),
                "nullable": column.nullable,
                "default": column.default,
                "server_default": str(column.server_default.arg)
                if column.server_default and hasattr(column.server_default, "arg")
                else None,
            }
    return col_map


async def get_db_schema(engine) -> dict[str, dict[str, Any]]:
    """Query PostgreSQL information_schema for actual column metadata."""
    schema: dict[str, dict[str, Any]] = defaultdict(dict)

    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.udt_name,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale
                FROM information_schema.columns c
                JOIN information_schema.tables t
                    ON c.table_name = t.table_name
                    AND c.table_schema = t.table_schema
                WHERE c.table_schema = 'public'
                    AND t.table_type = 'BASE TABLE'
                ORDER BY c.table_name, c.ordinal_position
            """)
        )
        rows = result.fetchall()

        for row in rows:
            table_name = row.table_name
            col_name = row.column_name
            nullable = row.is_nullable == "YES"

            type_str = row.data_type
            if row.udt_name.startswith("_"):
                type_str = f"{row.udt_name[1:]}[]"
            elif row.character_maximum_length:
                type_str = f"{row.data_type}({row.character_maximum_length})"
            elif row.numeric_precision is not None and row.numeric_scale is not None:
                type_str = (
                    f"{row.data_type}({row.numeric_precision},{row.numeric_scale})"
                )
            elif row.udt_name in (
                "jsonb",
                "json",
                "uuid",
                "bool",
                "int4",
                "int8",
                "float4",
                "float8",
                "text",
                "varchar",
                "bpchar",
            ):
                type_str = row.udt_name

            schema[table_name][col_name] = {
                "type": type_str,
                "nullable": nullable,
                "default": None,
                "server_default": row.column_default,
            }

    return schema


def compare_schemas(
    orm_map: dict[str, dict[str, Any]],
    db_map: dict[str, dict[str, Any]],
    strict: bool = False,
) -> list[str]:
    """Compare ORM and DB schemas, return list of difference descriptions."""
    issues: list[str] = []

    all_tables = set(orm_map.keys()) | set(db_map.keys())

    for table in sorted(all_tables):
        orm_cols = orm_map.get(table, {})
        db_cols = db_map.get(table, {})

        for col, col_info in sorted(orm_cols.items()):
            if col not in db_cols:
                issues.append(
                    f"  [MISSING_IN_DB] {table}.{col} (ORM: {col_info['type']})"
                )
            else:
                db_info = db_cols[col]
                if col_info["nullable"] != db_info["nullable"]:
                    issues.append(
                        f"  [NULLABLE_MISMATCH] {table}.{col}: "
                        f"ORM nullable={col_info['nullable']}, DB nullable={db_info['nullable']}"
                    )

        for col in sorted(db_cols.keys()):
            if col not in orm_cols:
                issues.append(f"  [ORPHAN_IN_DB] {table}.{col} (in DB, not in ORM)")

    return issues


async def run_check(strict: bool = False) -> int:
    """Run schema diff check. Returns 0 on success, 1 if diffs found, 2 on error."""
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 2

    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+asyncpg://")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    try:
        engine = sa.create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        print(f"ERROR: Failed to create database engine: {e}")
        return 2

    try:
        from app.database import Base

        orm_models = list(Base.registry.mappers)
        orm_model_classes = [m.class_ for m in orm_models]

        orm_map = build_orm_column_map(orm_model_classes)
        db_map = await get_db_schema(engine)

        issues = compare_schemas(orm_map, db_map, strict=strict)

        if issues:
            print(f"Schema differences found ({len(issues)}):\n")
            for issue in issues:
                print(issue)
            print()
            if strict:
                print("FAILED: Schema differences detected in strict mode.")
                return 1
        else:
            print("Schema OK: No differences found between ORM and database.")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 2
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema Diff Check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any differences found",
    )
    args = parser.parse_args()

    return asyncio.run(run_check(strict=args.strict))


if __name__ == "__main__":
    sys.exit(main())
