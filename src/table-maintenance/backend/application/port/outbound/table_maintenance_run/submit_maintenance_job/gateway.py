"""Define the SubmitMaintenanceJobGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.submit_maintenance_job.input import (
        SubmitMaintenanceJobGatewayInput,
    )
    from application.port.outbound.table_maintenance_run.submit_maintenance_job.output import (
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
