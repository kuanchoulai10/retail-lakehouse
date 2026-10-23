"""Define the RecordingSendMaintenanceResultGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.workflow.send_maintenance_result import (
    SendMaintenanceResultGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.workflow.send_maintenance_result import (
        SendMaintenanceResultGatewayInput,
    )


class RecordingSendMaintenanceResultGateway(SendMaintenanceResultGateway):
    """Record every result instead of sending it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[SendMaintenanceResultGatewayInput] = []

    def send(self, input: SendMaintenanceResultGatewayInput) -> None:  # noqa: A002
        """Record the call."""
        self.calls.append(input)
