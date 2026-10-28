"""Define the RecordingSubmitMaintenanceJobGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGateway,
    SubmitMaintenanceJobGatewayOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run import (
        SubmitMaintenanceJobGatewayInput,
    )


class RecordingSubmitMaintenanceJobGateway(SubmitMaintenanceJobGateway):
    """Record every submit and keep one job per ``(run_id, operation, attempt)``."""

    def __init__(self) -> None:
        """Start with no jobs."""
        self.calls: list[SubmitMaintenanceJobGatewayInput] = []
        self.jobs: dict[str, SubmitMaintenanceJobGatewayInput] = {}

    @staticmethod
    def job_name(run_id: str, operation: str, attempt: int) -> str:
        """Name the job of one attempt, deterministically."""
        return f"job-{run_id}-{operation}-{attempt}"

    def submit(
        self,
        input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
    ) -> SubmitMaintenanceJobGatewayOutput:
        """Record the call; a repeated attempt keeps the first job."""
        self.calls.append(input)
        name = self.job_name(input.run_id, input.operation, input.attempt)
        self.jobs.setdefault(name, input)
        return SubmitMaintenanceJobGatewayOutput(job_name=name)
