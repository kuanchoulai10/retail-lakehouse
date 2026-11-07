"""Provide the create_schema function."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine

AGGREGATE_SQL_PACKAGES = (
    "context.table_maintenance.adapter.outbound.table_discovery_settings.sql",
    "context.table_maintenance.adapter.outbound.table_discovery_rule.sql",
    "context.table_maintenance.adapter.outbound.table_maintenance_run.sql",
    "context.table_maintenance.adapter.outbound.table.sql",
    "context.table_maintenance.adapter.outbound.table_maintenance_preset.sql",
)


def create_schema(engine: Engine) -> None:
    """Create every control-plane table that does not exist yet.

    The aggregate SQL packages register their tables on ``metadata`` when they
    are imported, and they import this package for ``metadata``. They are
    therefore imported here, on call, so the package import stays acyclic.
    """
    for package in AGGREGATE_SQL_PACKAGES:
        importlib.import_module(package)
    metadata.create_all(engine)
