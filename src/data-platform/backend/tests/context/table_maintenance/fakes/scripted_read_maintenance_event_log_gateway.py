"""Define the ScriptedReadMaintenanceEventLogGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceEventLogGateway,
    ReadMaintenanceEventLogGatewayOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceEventLogGatewayInput,
    )


class ScriptedReadMaintenanceEventLogGateway(ReadMaintenanceEventLogGateway):
    """Serve the event log state configured per execution, unknown by default, and record each read."""

    def __init__(self) -> None:
        """Start with no known event logs and no failure."""
        self.finished: dict[str, bool] = {}
        self.calls: list[ReadMaintenanceEventLogGatewayInput] = []
        self.error: Exception | None = None

    def read(
        self,
        input: ReadMaintenanceEventLogGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceEventLogGatewayOutput:
        """Return the configured state, or None; raise the configured error first."""
        self.calls.append(input)
        if self.error is not None:
            raise self.error
        return ReadMaintenanceEventLogGatewayOutput(finished=self.finished.get(input.execution_id))
