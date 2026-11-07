"""Define the DeleteMaintenanceJobGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.delete_maintenance_job.input import (
        DeleteMaintenanceJobGatewayInput,
    )


class DeleteMaintenanceJobGateway(Gateway):
    """Delete a maintenance job."""

    @abstractmethod
    def delete(self, input: DeleteMaintenanceJobGatewayInput) -> None:  # noqa: A002
        """Delete the job; deleting a missing job is a no-op."""
