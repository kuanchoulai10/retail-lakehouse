"""Define the ReadMaintenanceEventLogGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_event_log.input import (  # noqa: E501
        ReadMaintenanceEventLogGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.read_maintenance_event_log.output import (  # noqa: E501
        ReadMaintenanceEventLogGatewayOutput,
    )


class ReadMaintenanceEventLogGateway(Gateway):
    """Read whether the event log of one execution of a maintenance job was closed cleanly."""

    @abstractmethod
    def read(self, input: ReadMaintenanceEventLogGatewayInput) -> ReadMaintenanceEventLogGatewayOutput:  # noqa: A002
        """Return whether the execution's event log finished, did not finish, or cannot be found."""
