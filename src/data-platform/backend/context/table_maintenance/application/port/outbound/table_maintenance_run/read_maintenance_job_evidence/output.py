"""Define the ReadMaintenanceJobEvidenceGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_evidence.job_container_exit import (  # noqa: E501
        JobContainerExit,
    )


@dataclass(frozen=True)
class ReadMaintenanceJobEvidenceGatewayOutput:
    """Carry the execution id, the job error, the terminated containers and the driver start of one attempt.

    ``driver_started_at`` is an ISO-8601 time, None when the driver never started or its pod is gone.
    """

    execution_id: str | None
    error: str | None
    containers: tuple[JobContainerExit, ...] = field(default_factory=tuple)
    driver_started_at: str | None = None
