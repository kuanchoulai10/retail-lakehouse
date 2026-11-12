"""Define the ReadMaintenanceJobPodsGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_pods.input import (  # noqa: E501
        ReadMaintenanceJobPodsGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_pods.output import (  # noqa: E501
        ReadMaintenanceJobPodsGatewayOutput,
    )


class ReadMaintenanceJobPodsGateway(Gateway):
    """Read the pods of one maintenance job attempt that can still run."""

    @abstractmethod
    def read(self, input: ReadMaintenanceJobPodsGatewayInput) -> ReadMaintenanceJobPodsGatewayOutput:  # noqa: A002
        """Return the names of the attempt's live pods; none once every pod has stopped or is gone."""
