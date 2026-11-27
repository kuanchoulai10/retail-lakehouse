"""Shared SQL infrastructure for the outbound adapters.

Provides the shared ``metadata``, the engine factory, the UTC datetime column
type, the datetime JSON codec, ``create_schema``, ``add_missing_columns``,
``add_missing_indexes`` and the policy placements store, which reads across
the catalogs, namespaces and tables rows.
"""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.shared.sql.add_missing_columns import (
    add_missing_columns,
)
from context.table_maintenance.adapter.outbound.shared.sql.add_missing_indexes import (
    add_missing_indexes,
)
from context.table_maintenance.adapter.outbound.shared.sql.create_schema import (
    AGGREGATE_SQL_PACKAGES,
    create_schema,
)
from context.table_maintenance.adapter.outbound.shared.sql.iso_datetime_codec import (
    IsoDatetimeCodec,
)
from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata
from context.table_maintenance.adapter.outbound.shared.sql.policy_placements_sql_store import (
    PolicyPlacementsSqlStore,
)
from context.table_maintenance.adapter.outbound.shared.sql.utc_date_time import (
    UtcDateTime,
)

__all__ = [
    "AGGREGATE_SQL_PACKAGES",
    "IsoDatetimeCodec",
    "PolicyPlacementsSqlStore",
    "UtcDateTime",
    "add_missing_columns",
    "add_missing_indexes",
    "create_schema",
    "metadata",
]
