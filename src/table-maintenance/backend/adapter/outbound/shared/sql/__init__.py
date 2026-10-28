"""Shared SQL infrastructure for the outbound adapters.

Provides the shared ``metadata``, the engine factory, the UTC datetime column
type, the JSON codecs and ``create_schema``.
"""

from __future__ import annotations

from adapter.outbound.shared.sql.create_schema import create_schema
from adapter.outbound.shared.sql.iso_datetime_codec import IsoDatetimeCodec
from adapter.outbound.shared.sql.maintenance_settings_codec import (
    MaintenanceSettingsCodec,
)
from adapter.outbound.shared.sql.metadata import metadata
from adapter.outbound.shared.sql.utc_date_time import UtcDateTime

__all__ = [
    "IsoDatetimeCodec",
    "MaintenanceSettingsCodec",
    "UtcDateTime",
    "create_schema",
    "metadata",
]
