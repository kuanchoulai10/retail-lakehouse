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


def test_create_schema_creates_the_tables_of_the_nine_aggregates():
    """The schema holds the tables of the nine aggregates, the discovery policies and their attachments included."""
    assert {package.split(".")[-2] for package in AGGREGATE_SQL_PACKAGES} == {
        "catalog_discovery",
        "table",
        "table_discovery_policy",
        "table_discovery_policy_attachment",
        "table_discovery_rules",
        "table_maintenance_policy",
        "table_maintenance_policy_attachment",
        "table_maintenance_run",
        "table_reconciliation",
    }


def test_create_schema_adds_columns_an_older_release_did_not_create(tmp_path: Path) -> None:
    """A table stored by an older release gets the columns added since, when the schema is created again."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE table_maintenance_runs DROP COLUMN priority"))
    create_schema(engine)
    assert "priority" in {c["name"] for c in inspect(engine).get_columns("table_maintenance_runs")}


def test_create_schema_creates_the_table_metrics_table(tmp_path: Path) -> None:
    """The newest metrics of each table are kept in the table_metrics table."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    create_schema(engine)
    assert "table_metrics" in inspect(engine).get_table_names()
