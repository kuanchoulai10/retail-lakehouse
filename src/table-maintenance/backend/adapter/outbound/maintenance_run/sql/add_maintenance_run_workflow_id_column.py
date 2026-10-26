"""Provide the add_maintenance_run_workflow_id_column schema upgrade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import inspect, text

if TYPE_CHECKING:
    from sqlalchemy import Engine


def add_maintenance_run_workflow_id_column(engine: Engine) -> None:
    """Add ``maintenance_runs.workflow_id`` to a table created before it existed.

    ``create_all`` never alters an existing table, so this adds the column with an
    empty default and backfills every older row with the workflow id it was
    started under, ``maintenance-{run_id}``. A table that has the column is left
    untouched, so calling it again is a no-op.
    """
    columns = {c["name"] for c in inspect(engine).get_columns("maintenance_runs")}
    if "workflow_id" in columns:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE maintenance_runs "
                "ADD COLUMN workflow_id VARCHAR NOT NULL DEFAULT ''"
            )
        )
        conn.execute(
            text(
                "UPDATE maintenance_runs SET workflow_id = 'maintenance-' || id "
                "WHERE workflow_id = ''"
            )
        )
