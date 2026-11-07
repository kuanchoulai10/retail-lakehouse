"""Shared SQL infrastructure for the outbound adapters.

Provides the shared ``metadata``, the engine factory, the UTC datetime column
type, the JSON codecs and ``create_schema``.
"""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.shared.sql.create_schema import (
    AGGREGATE_SQL_PACKAGES,
    create_schema,
)
from context.table_maintenance.adapter.outbound.shared.sql.iso_datetime_codec import (
    IsoDatetimeCodec,
)
from context.table_maintenance.adapter.outbound.shared.sql.maintenance_settings_codec import (
    MaintenanceSettingsCodec,
)
from context.table_maintenance.adapter.outbound.shared.sql.metadata import metadata
from context.table_maintenance.adapter.outbound.shared.sql.utc_date_time import (
    UtcDateTime,
)

__all__ = [
    "AGGREGATE_SQL_PACKAGES",
    "IsoDatetimeCodec",
    "MaintenanceSettingsCodec",
    "UtcDateTime",
    "create_schema",
    "metadata",
]
