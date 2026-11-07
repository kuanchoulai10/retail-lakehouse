"""Define the SubmitMaintenanceJobGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.input import (
        SubmitMaintenanceJobGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.output import (  # noqa: E501
        SubmitMaintenanceJobGatewayOutput,
    )


class SubmitMaintenanceJobGateway(Gateway):
    """Submit a maintenance job."""

    @abstractmethod
    def submit(
        self,
        input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
    ) -> SubmitMaintenanceJobGatewayOutput:
        """Submit the job and return its name.

        Submitting the same ``(run_id, operation, attempt)`` twice leaves one job.
        """
