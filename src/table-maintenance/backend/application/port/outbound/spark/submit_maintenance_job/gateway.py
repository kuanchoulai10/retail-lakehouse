"""Define the SubmitMaintenanceJobGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.spark.submit_maintenance_job.input import (
        SubmitMaintenanceJobGatewayInput,
    )


class SubmitMaintenanceJobGateway(Gateway):
    """Submit a maintenance job to Spark."""

    @abstractmethod
    def submit(self, input: SubmitMaintenanceJobGatewayInput) -> None:  # noqa: A002
        """Submit the job; submitting the same ``app_name`` twice leaves one job."""
