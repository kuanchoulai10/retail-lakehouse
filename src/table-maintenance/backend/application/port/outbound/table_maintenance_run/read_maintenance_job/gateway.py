"""Define the ReadMaintenanceJobGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.read_maintenance_job.input import (
        ReadMaintenanceJobGatewayInput,
    )
    from application.port.outbound.table_maintenance_run.read_maintenance_job.output import (
        ReadMaintenanceJobGatewayOutput,
    )


class ReadMaintenanceJobGateway(Gateway):
    """Read the state of a maintenance job."""

    @abstractmethod
    def read(
        self, input: ReadMaintenanceJobGatewayInput
    ) -> ReadMaintenanceJobGatewayOutput:  # noqa: A002
        """Return the job state: PENDING, RUNNING, COMPLETED, FAILED or NOT_FOUND."""
