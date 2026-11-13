"""Guard create_schema's list of aggregate SQL packages against drift."""

from __future__ import annotations

import importlib
from pathlib import Path

from sqlalchemy import Table, create_engine, inspect, text

from context.table_maintenance.adapter.outbound.shared.sql import (
    AGGREGATE_SQL_PACKAGES,
    create_schema,
    metadata,
)

BACKEND = Path(__file__).resolve().parents[7]
SHARED_SQL = "context.table_maintenance.adapter.outbound.shared.sql"


def _registered_tables(package: str) -> list[Table]:
    module = importlib.import_module(package)
    values = (getattr(module, name) for name in module.__all__)
    return [v for v in values if isinstance(v, Table) and v.metadata is metadata]


def _sql_packages() -> set[str]:
    return {
        ".".join(init.parent.relative_to(BACKEND).parts)
        for init in (BACKEND / "context" / "table_maintenance" / "adapter" / "outbound").glob("*/sql/__init__.py")
    }


def test_create_schema_lists_every_sql_package_that_defines_tables():
    """The schema creation lists each SQL package that defines tables exactly once."""
    defining = {p for p in _sql_packages() - {SHARED_SQL} if _registered_tables(p)}
    assert set(AGGREGATE_SQL_PACKAGES) == defining
    assert len(AGGREGATE_SQL_PACKAGES) == len(set(AGGREGATE_SQL_PACKAGES))


def test_shared_sql_defines_no_table():
    """shared/sql holds only the metadata, column types and codecs, so it is excluded."""
    assert _registered_tables(SHARED_SQL) == []


def test_create_schema_includes_the_reconciliations_package():
    """The reconciliation records table is created with the control-plane schema."""
    assert "context.table_maintenance.adapter.outbound.table_reconciliation.sql" in AGGREGATE_SQL_PACKAGES


def test_create_schema_includes_the_compaction_candidates_package():
    """The compaction candidates table is created with the control-plane schema."""
    assert "context.table_maintenance.adapter.outbound.compaction_candidate.sql" in AGGREGATE_SQL_PACKAGES


def test_create_schema_adds_columns_an_older_release_did_not_create(tmp_path: Path) -> None:
    """A table stored by an older release gets the columns added since, when the schema is created again."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE compaction_candidates DROP COLUMN waiting_since"))
    create_schema(engine)
    assert "waiting_since" in {c["name"] for c in inspect(engine).get_columns("compaction_candidates")}
