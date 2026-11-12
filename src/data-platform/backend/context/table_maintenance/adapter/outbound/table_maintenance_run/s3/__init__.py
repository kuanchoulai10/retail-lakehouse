"""Object-store adapters of the maintenance run aggregate."""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.table_maintenance_run.s3.read_maintenance_event_log_s3_gateway import (  # noqa: E501
    ReadMaintenanceEventLogS3Gateway,
)

__all__ = [
    "ReadMaintenanceEventLogS3Gateway",
]
