"""Define the RecordingDeleteMaintenanceJobGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table_maintenance_run.delete_maintenance_job import (
    DeleteMaintenanceJobGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.delete_maintenance_job import (
        DeleteMaintenanceJobGatewayInput,
    )


class RecordingDeleteMaintenanceJobGateway(DeleteMaintenanceJobGateway):
    """Record every delete instead of performing it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[DeleteMaintenanceJobGatewayInput] = []

    def delete(self, input: DeleteMaintenanceJobGatewayInput) -> None:  # noqa: A002
        """Record the call."""
        self.calls.append(input)
