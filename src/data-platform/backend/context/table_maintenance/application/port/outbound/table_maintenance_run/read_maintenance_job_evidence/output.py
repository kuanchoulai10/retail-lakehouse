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
    """Carry the execution id, the job error and the terminated containers of one attempt."""

    execution_id: str | None
    error: str | None
    containers: tuple[JobContainerExit, ...] = field(default_factory=tuple)
