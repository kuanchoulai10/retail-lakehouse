"""Provide the add_missing_indexes function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import inspect

from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine, Index, MetaData

logger = logging.getLogger(__name__)


def add_missing_indexes(engine: Engine, *, schema: MetaData | None = None) -> list[str]:
    """Create each index of ``schema`` (the shared metadata by default) that a stored table lacks.

    ``create_all`` creates indexes only with a new table, so a table created
    by an older release lacks the indexes declared since. A table not created
    yet is left alone. Returns ``"<table>.<index>"`` for each index created, in
    table order.
    """
    tables = (metadata if schema is None else schema).sorted_tables
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing: list[Index] = []
    for table in tables:
        if table.name not in existing:
            continue
        stored = {i["name"] for i in inspector.get_indexes(table.name)}
        missing.extend(i for i in sorted(table.indexes, key=lambda i: str(i.name)) if i.name not in stored)
    with engine.begin() as connection:
        for index in missing:
            index.create(connection)
            logger.info("created index %s.%s", index.table.name if index.table is not None else "?", index.name)
    return [f"{i.table.name if i.table is not None else '?'}.{i.name}" for i in missing]
