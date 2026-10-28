"""Define the SendMaintenanceResultGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.send_maintenance_result.input import (
        SendMaintenanceResultGatewayInput,
    )


class SendMaintenanceResultGateway(Gateway):
    """Report a maintenance operation result to the run that waits for it."""

    @abstractmethod
    def send(self, input: SendMaintenanceResultGatewayInput) -> None:  # noqa: A002
        """Deliver the result, raising NotFoundError when the run is no longer waiting."""
