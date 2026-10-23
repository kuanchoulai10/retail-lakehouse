"""Define the RecordingSubmitMaintenanceJobGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.spark.submit_maintenance_job import (
    SubmitMaintenanceJobGateway,
)

if TYPE_CHECKING:
    from application.port.outbound.spark.submit_maintenance_job import (
        SubmitMaintenanceJobGatewayInput,
    )


class RecordingSubmitMaintenanceJobGateway(SubmitMaintenanceJobGateway):
    """Record every submit and keep one job per application name."""

    def __init__(self) -> None:
        """Start with no jobs."""
        self.calls: list[SubmitMaintenanceJobGatewayInput] = []
        self.jobs: dict[str, SubmitMaintenanceJobGatewayInput] = {}

    def submit(self, input: SubmitMaintenanceJobGatewayInput) -> None:  # noqa: A002
        """Record the call; a repeated application name keeps the first job."""
        self.calls.append(input)
        self.jobs.setdefault(input.app_name, input)
