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
    """Serve the live pods and driver start configured per attempt, record each read and fail when told."""

    def __init__(self) -> None:
        """Start with no live pods, no driver start and no failure."""
        self.live_pods: dict[tuple[str, str, int], tuple[str, ...]] = {}
        self.driver_started_at: dict[tuple[str, str, int], str] = {}
        self.calls: list[ReadMaintenanceJobPodsGatewayInput] = []
        self.error: Exception | None = None

    def set_live_pods(self, run_id: str, operation: str, attempt: int, *names: str) -> None:
        """Configure the live pods returned for one operation attempt."""
        self.live_pods[(run_id, operation, attempt)] = names

    def set_driver_started_at(self, run_id: str, operation: str, attempt: int, started_at: str) -> None:
        """Configure the driver start (an ISO-8601 time) returned for one operation attempt."""
        self.driver_started_at[(run_id, operation, attempt)] = started_at

    def read(
        self,
        input: ReadMaintenanceJobPodsGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobPodsGatewayOutput:
        """Return the configured live pods and driver start, or none; raise the configured error first."""
        self.calls.append(input)
        if self.error is not None:
            raise self.error
        key = (input.run_id, input.operation, input.attempt)
        return ReadMaintenanceJobPodsGatewayOutput(
            live_pods=self.live_pods.get(key, ()), driver_started_at=self.driver_started_at.get(key)
        )
