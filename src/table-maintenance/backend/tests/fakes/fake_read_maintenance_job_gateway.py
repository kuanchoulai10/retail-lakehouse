"""Define the FakeReadMaintenanceJobGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.spark.read_maintenance_job import (
    ReadMaintenanceJobGateway,
    ReadMaintenanceJobGatewayOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.spark.read_maintenance_job import (
        ReadMaintenanceJobGatewayInput,
    )


class FakeReadMaintenanceJobGateway(ReadMaintenanceJobGateway):
    """Serve job states configured by the test, NOT_FOUND by default."""

    def __init__(self) -> None:
        """Start with no configured jobs."""
        self.states: dict[str, ReadMaintenanceJobGatewayOutput] = {}
        self.calls: list[ReadMaintenanceJobGatewayInput] = []

    def set_state(self, app_name: str, state: str, error: str | None = None) -> None:
        """Configure the state returned for an application name."""
        self.states[app_name] = ReadMaintenanceJobGatewayOutput(state, error)

    def read(
        self,
        input: ReadMaintenanceJobGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobGatewayOutput:
        """Return the configured state, or NOT_FOUND."""
        self.calls.append(input)
        return self.states.get(
            input.app_name, ReadMaintenanceJobGatewayOutput("NOT_FOUND")
        )
