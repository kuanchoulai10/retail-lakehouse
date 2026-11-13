"""Provide the add_missing_columns function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Column, Engine, MetaData, Table

logger = logging.getLogger(__name__)


def add_missing_columns(engine: Engine, *, schema: MetaData | None = None) -> list[str]:
    """Add each column of ``schema`` (the shared metadata by default) that a stored table lacks.

    ``create_all`` creates only missing tables, so a table created by an older
    release keeps its old columns; this brings it up to date with
    ``ALTER TABLE ... ADD COLUMN``. A table not created yet is left alone. A new
    column must be nullable or carry a ``server_default``, since rows already
    stored need a value; otherwise nothing is added and ``ValueError`` names the
    column. Returns ``"<table>.<column>"`` for each column added, in table order.
    """
    tables = (metadata if schema is None else schema).sorted_tables
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing: list[tuple[Table, Column]] = []
    for table in tables:
        if table.name not in existing:
            continue
        stored = {c["name"] for c in inspector.get_columns(table.name)}
        missing.extend((table, column) for column in table.columns if column.name not in stored)
    refused = [f"{t.name}.{c.name}" for t, c in missing if not c.nullable and c.server_default is None]
    if refused:
        raise ValueError(f"cannot add a not-null column without a server default: {', '.join(refused)}")
    preparer = engine.dialect.identifier_preparer
    with engine.begin() as connection:
        for table, column in missing:
            spec = CreateColumn(column).compile(dialect=engine.dialect)
            connection.execute(text(f"ALTER TABLE {preparer.format_table(table)} ADD COLUMN {spec}"))
            logger.info("added column %s.%s", table.name, column.name)
    return [f"{t.name}.{c.name}" for t, c in missing]
