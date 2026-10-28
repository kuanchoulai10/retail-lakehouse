"""Define the RecordingSendDiscoveryRequestGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table.send_discovery_request import (
    SendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.table.send_discovery_request import (
        SendDiscoveryRequestGatewayInput,
    )


class RecordingSendDiscoveryRequestGateway(SendDiscoveryRequestGateway):
    """Record every discovery request instead of sending it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[SendDiscoveryRequestGatewayInput] = []

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Record the call."""
        self.calls.append(input)
