"""Temporal-backed gateways of the table maintenance run aggregate."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.outbound.table_maintenance_run.send_maintenance_result_temporal_gateway import (  # noqa: E501
    SendMaintenanceResultTemporalGateway,
)

__all__ = [
    "SendMaintenanceResultTemporalGateway",
]
