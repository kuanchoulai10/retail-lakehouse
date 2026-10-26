"""Define the SendMaintenanceResultGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.workflow.send_maintenance_result.input import (
        SendMaintenanceResultGatewayInput,
    )


class SendMaintenanceResultGateway(Gateway):
    """Send a maintenance result to the workflow."""

    @abstractmethod
    def send(self, input: SendMaintenanceResultGatewayInput) -> None:  # noqa: A002
        """Signal the table maintenance workflow with the result."""
