"""Define the RecordingUpdateDiscoveryScheduleGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.discovery.update_discovery_schedule import (
    UpdateDiscoveryScheduleGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.discovery.update_discovery_schedule import (
        UpdateDiscoveryScheduleGatewayInput,
    )


class RecordingUpdateDiscoveryScheduleGateway(UpdateDiscoveryScheduleGateway):
    """Record every schedule update instead of applying it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[UpdateDiscoveryScheduleGatewayInput] = []

    def update(self, input: UpdateDiscoveryScheduleGatewayInput) -> None:  # noqa: A002
        """Record the call."""
        self.calls.append(input)
