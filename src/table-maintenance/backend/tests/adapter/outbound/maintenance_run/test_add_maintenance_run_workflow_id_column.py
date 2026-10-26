"""Test the schema upgrade that adds maintenance_runs.workflow_id."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from adapter.outbound.maintenance_run.sql.add_maintenance_run_workflow_id_column import (
    add_maintenance_run_workflow_id_column,
)
from adapter.outbound.sql.create_schema import create_schema

_LEGACY_DDL = """
CREATE TABLE maintenance_runs (
    id VARCHAR PRIMARY KEY,
    table_uuid VARCHAR NOT NULL,
    "trigger" VARCHAR NOT NULL,
    operations_json JSON NOT NULL,
    created_at DATETIME NOT NULL,
    finished_at DATETIME
)
"""


def _legacy_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as conn:
        conn.execute(text(_LEGACY_DDL))
        conn.execute(
            text(
                "INSERT INTO maintenance_runs VALUES "
                "('r1', 'u1', 'scheduled', '[]', '2026-10-24 00:00:00', NULL)"
            )
        )
    return engine


def _columns(engine) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns("maintenance_runs")}


def test_adds_the_column_and_backfills_the_legacy_workflow_id():
    engine = _legacy_engine()

    add_maintenance_run_workflow_id_column(engine)

    assert "workflow_id" in _columns(engine)
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT workflow_id FROM maintenance_runs WHERE id = 'r1'")
        ).scalar_one()
    assert value == "maintenance-r1"


def test_is_idempotent():
    engine = _legacy_engine()

    add_maintenance_run_workflow_id_column(engine)
    add_maintenance_run_workflow_id_column(engine)

    assert "workflow_id" in _columns(engine)


def test_create_schema_upgrades_a_legacy_table():
    engine = _legacy_engine()

    create_schema(engine)

    assert "workflow_id" in _columns(engine)


def test_a_fresh_schema_already_has_the_column():
    engine = create_engine("sqlite://")

    create_schema(engine)

    assert "workflow_id" in _columns(engine)
