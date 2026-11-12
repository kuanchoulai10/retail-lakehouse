"""Define the ScriptedReadMaintenanceJobEvidenceGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobEvidenceGateway,
    ReadMaintenanceJobEvidenceGatewayOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobEvidenceGatewayInput,
    )

NO_EVIDENCE = ReadMaintenanceJobEvidenceGatewayOutput(execution_id=None, error=None)


class ScriptedReadMaintenanceJobEvidenceGateway(ReadMaintenanceJobEvidenceGateway):
    """Serve the evidence configured per attempt, none by default, record each read, and fail when told."""

    def __init__(self) -> None:
        """Start with no evidence and no failure."""
        self.evidence: dict[tuple[str, str, int], ReadMaintenanceJobEvidenceGatewayOutput] = {}
        self.calls: list[ReadMaintenanceJobEvidenceGatewayInput] = []
        self.error: Exception | None = None

    def set_evidence(
        self, run_id: str, operation: str, attempt: int, evidence: ReadMaintenanceJobEvidenceGatewayOutput
    ) -> None:
        """Configure the evidence returned for one operation attempt."""
        self.evidence[(run_id, operation, attempt)] = evidence

    def read(
        self,
        input: ReadMaintenanceJobEvidenceGatewayInput,  # noqa: A002
    ) -> ReadMaintenanceJobEvidenceGatewayOutput:
        """Return the configured evidence, or none; raise the configured error first."""
        self.calls.append(input)
        if self.error is not None:
            raise self.error
        return self.evidence.get((input.run_id, input.operation, input.attempt), NO_EVIDENCE)
