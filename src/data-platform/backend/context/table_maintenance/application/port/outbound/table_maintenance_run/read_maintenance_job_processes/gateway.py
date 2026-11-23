"""Define the ReadMaintenanceJobProcessesGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_processes.input import (  # noqa: E501
        ReadMaintenanceJobProcessesGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_processes.output import (  # noqa: E501
        ReadMaintenanceJobProcessesGatewayOutput,
    )


class ReadMaintenanceJobProcessesGateway(Gateway):
    """Read the processes of one maintenance job attempt that can still run."""

    @abstractmethod
    def read(self, input: ReadMaintenanceJobProcessesGatewayInput) -> ReadMaintenanceJobProcessesGatewayOutput:  # noqa: A002
        """Return the names of the attempt's live processes; none once every process has stopped or is gone."""
