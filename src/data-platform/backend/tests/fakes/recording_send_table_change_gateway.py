"""Define the RecordingSendTableChangeGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table import SendTableChangeGateway

if TYPE_CHECKING:
    from application.port.outbound.table import SendTableChangeGatewayInput


class RecordingSendTableChangeGateway(SendTableChangeGateway):
    """Record every table change instead of sending it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[SendTableChangeGatewayInput] = []

    def send(self, input: SendTableChangeGatewayInput) -> None:  # noqa: A002
        """Record the call; every change must name the table it is about."""
        assert input.table_name, f"change {input.change} carries no table name"
        self.calls.append(input)
