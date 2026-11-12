"""Define the ScriptedReadMaintenanceJobPodsGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobPodsGateway,
    ReadMaintenanceJobPodsGatewayOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobPodsGatewayInput,
    )


class ScriptedReadMaintenanceJobPodsGateway(ReadMaintenanceJobPodsGateway):
    """Serve the live pods configured per attempt, none by default, and record each read."""

    def __init__(self) -> None:
        """Start with no live pods."""
        self.live_pods: dict[tuple[str, str, int], tuple[str, ...]] = {}
        self.calls: list[ReadMaintenanceJobPodsGatewayInput] = []

    def set_live_pods(self, run_id: str, operation: str, attempt: int, *names: str) -> None:
        """Configure the live pods returned for one operation attempt."""
        self.live_pods[(run_id, operation, attempt)] = names

    def read(
        self,
        input: ReadMaintenanceJobPodsGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobPodsGatewayOutput:
        """Return the configured live pods, or none."""
        self.calls.append(input)
        return ReadMaintenanceJobPodsGatewayOutput(
            live_pods=self.live_pods.get((input.run_id, input.operation, input.attempt), ())
        )
