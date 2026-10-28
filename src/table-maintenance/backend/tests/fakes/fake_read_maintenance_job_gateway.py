"""Define the FakeReadMaintenanceJobGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobGateway,
    ReadMaintenanceJobGatewayOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobGatewayInput,
    )


class FakeReadMaintenanceJobGateway(ReadMaintenanceJobGateway):
    """Serve job states configured by the test, NOT_FOUND by default."""

    def __init__(self) -> None:
        """Start with no configured jobs."""
        self.states: dict[tuple[str, str, int], ReadMaintenanceJobGatewayOutput] = {}
        self.calls: list[ReadMaintenanceJobGatewayInput] = []

    def set_state(
        self,
        run_id: str,
        operation: str,
        attempt: int,
        state: str,
        error: str | None = None,
    ) -> None:
        """Configure the state returned for one operation attempt."""
        self.states[(run_id, operation, attempt)] = ReadMaintenanceJobGatewayOutput(
            state, error
        )

    def read(
        self,
        input: ReadMaintenanceJobGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobGatewayOutput:
        """Return the configured state, or NOT_FOUND."""
        self.calls.append(input)
        return self.states.get(
            (input.run_id, input.operation, input.attempt),
            ReadMaintenanceJobGatewayOutput("NOT_FOUND"),
        )
