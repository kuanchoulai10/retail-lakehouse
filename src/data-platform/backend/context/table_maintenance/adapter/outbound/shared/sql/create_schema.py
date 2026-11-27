"""Provide the create_schema function."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.shared.sql.add_missing_columns import add_missing_columns
from context.table_maintenance.adapter.outbound.shared.sql.add_missing_indexes import add_missing_indexes
from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine

AGGREGATE_SQL_PACKAGES = (
    "context.table_maintenance.adapter.outbound.catalog.sql",
    "context.table_maintenance.adapter.outbound.namespace.sql",
    "context.table_maintenance.adapter.outbound.catalog_discovery.sql",
    "context.table_maintenance.adapter.outbound.table_discovery_policy.sql",
    "context.table_maintenance.adapter.outbound.table_discovery_policy_attachment.sql",
    "context.table_maintenance.adapter.outbound.table_maintenance_run.sql",
    "context.table_maintenance.adapter.outbound.table_reconciliation.sql",
    "context.table_maintenance.adapter.outbound.table.sql",
    "context.table_maintenance.adapter.outbound.table_maintenance_policy.sql",
    "context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql",
)


def create_schema(engine: Engine) -> None:
    """Create every control-plane table that does not exist yet, and add the columns and indexes a stored one lacks.

    The aggregate SQL packages register their tables on ``metadata`` when they
    are imported, and they import this package for ``metadata``. They are
    therefore imported here, on call, so the package import stays acyclic.
    ``create_all`` leaves an existing table as it is, so ``add_missing_columns``
    then adds the columns introduced since that table was created, and
    ``add_missing_indexes`` the indexes.
    """
    for package in AGGREGATE_SQL_PACKAGES:
        importlib.import_module(package)
    metadata.create_all(engine)
    add_missing_columns(engine)
    add_missing_indexes(engine)
