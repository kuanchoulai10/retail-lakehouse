"""Define the RecordingUpdateTableDiscoveryScheduleGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
    UpdateTableDiscoveryScheduleGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
        UpdateTableDiscoveryScheduleGatewayInput,
    )


class RecordingUpdateTableDiscoveryScheduleGateway(UpdateTableDiscoveryScheduleGateway):
    """Record every schedule update instead of applying it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[UpdateTableDiscoveryScheduleGatewayInput] = []

    def update(self, input: UpdateTableDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Record the call."""
        self.calls.append(input)
