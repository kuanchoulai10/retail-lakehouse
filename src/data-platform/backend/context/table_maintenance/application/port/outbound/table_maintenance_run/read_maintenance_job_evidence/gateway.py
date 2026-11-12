"""Define the ReadMaintenanceJobEvidenceGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_evidence.input import (  # noqa: E501
        ReadMaintenanceJobEvidenceGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_job_evidence.output import (  # noqa: E501
        ReadMaintenanceJobEvidenceGatewayOutput,
    )


class ReadMaintenanceJobEvidenceGateway(Gateway):
    """Read what one maintenance job attempt left behind about how it ended."""

    @abstractmethod
    def read(self, input: ReadMaintenanceJobEvidenceGatewayInput) -> ReadMaintenanceJobEvidenceGatewayOutput:  # noqa: A002
        """Return the attempt's execution id, its job error and its terminated containers.

        A job that no longer exists has no execution id and no error, but its containers may still be listed.
        """
