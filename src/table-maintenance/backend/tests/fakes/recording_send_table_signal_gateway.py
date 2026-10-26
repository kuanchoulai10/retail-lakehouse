"""Define the RecordingSendTableSignalGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGatewayInput,
    )


class RecordingSendTableSignalGateway(SendTableSignalGateway):
    """Record every signal instead of sending it."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[SendTableSignalGatewayInput] = []

    def send(self, input: SendTableSignalGatewayInput) -> None:  # noqa: A002
        """Record the call; every signal must name the table it is about."""
        assert input.table_name, f"signal {input.signal} carries no table name"
        self.calls.append(input)
