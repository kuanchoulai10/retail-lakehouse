"""Define the RecordingSendDiscoveryRequestGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        SendDiscoveryRequestGatewayInput,
    )


class RecordingSendDiscoveryRequestGateway(SendDiscoveryRequestGateway):
    """Record every discovery request instead of sending it.

    A request for a catalog in ``failing`` raises and is not recorded.
    """

    def __init__(self) -> None:
        """Start with no calls and no failing catalog."""
        self.calls: list[SendDiscoveryRequestGatewayInput] = []
        self.failing: set[str] = set()

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Record the call, or raise for a failing catalog."""
        if input.catalog in self.failing:
            msg = f"cannot start discovery in {input.catalog}"
            raise RuntimeError(msg)
        self.calls.append(input)
