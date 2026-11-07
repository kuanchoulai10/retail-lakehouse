"""Inbound Temporal adapter."""

from __future__ import annotations

from adapter.hybrid.temporal.inbound.ensure_table_discovery_schedule import (
    ensure_table_discovery_schedule,
)
from adapter.hybrid.temporal.inbound.ensure_table_maintenance_admission import (
    ensure_table_maintenance_admission,
)

__all__ = [
    "ensure_table_discovery_schedule",
    "ensure_table_maintenance_admission",
]
